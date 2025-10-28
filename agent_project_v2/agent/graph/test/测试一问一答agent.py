from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import Graph, END, StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, List
from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent_project_v2.agent.llm import chatGPT_llm
from langchain.tools import tool  # ✅ 直接使用装饰器
# from langgraph.prebuilt.tool_executor import ToolExecutor,ToolInvocation
from langgraph.prebuilt import ToolNode, ToolInvocation
from agent_project_v2.agent.utils import ColorPrinter
from langgraph.checkpoint.memory import InMemorySaver

# memory = SqliteSaver.from_conn_string("agent_memory.db")
memory = InMemorySaver()
color_printer = ColorPrinter()
class OverallState(TypedDict):
    input: str
    AI_answer: str
    messages: Annotated[List[BaseMessage], add_messages]
    action_result: list  # 存储工具调用结果
    tool_calls: list # 存储工具调用

@tool
def get_robot_end_pos_and_ori(description,robot_id):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID

    返回:
    - dict: API 响应数据，包含 `status`、`end_pos` 和 `end_ori`
    """

    try:
        result = {"end_pos": [0.5, 0.3, 0.2], "end_ori": [0, 0, 0, 1]}
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

graph = StateGraph(OverallState)

llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
llm_with_tools = llm.bind_tools([get_robot_end_pos_and_ori])
tool_executor = ToolNode(tools=[get_robot_end_pos_and_ori])
class AgentNode:
    def __init__(self,config):
        self.config = config

    def __call__(self, state: OverallState):
        messages = state.get("messages", [])
        input_text = state.get("input", "")
        action_result = state.get("action_result", [])
        system_message = SystemMessage(content="你是一个AI助理,请回答用户的问题,必要时可以使用工具\n")
        message_history = [system_message] + messages

        llm_output = llm_with_tools.invoke(message_history)


        messages.append(llm_output)

        tool_calls, current_action_result = self.toolcall_parsing(llm_output)
        if not tool_calls:
            return { "messages": messages,"tool_calls": None, "action_result": state.get("action_result", []),"AI_answer": llm_output.content}
        else:
            # return {"messages": messages}  # 返回更新后的消息历史
            return {"messages": messages, "action_result": action_result + current_action_result,"tool_calls":tool_calls

                    }
        pass

    def toolcall_parsing(self,llm_output):
        # 解析 llm output toolcalls
        current_action = []
        tool_calls = llm_output.tool_calls  # tool_calls 是一个 list
        if not tool_calls:
            return [], []
        else:
            for tool_call in tool_calls:
                task = tool_call.get('args').get('description')
                tool_name = tool_call.get('name')
                current_action.append({
                    "task_name": task,
                    "tool_name": tool_name,
                    "status": "pending execution",
                    "result": "",
                })
            return tool_calls,current_action

def input_node(state: OverallState):
    user_input = input("请输入您的问题（输入 'exit' 结束对话）：")
    # messages = state.get("messages", [])
    # messages.append(HumanMessage(content=user_input))
    return {"input":user_input,"messages": HumanMessage(content=user_input) }

def answer_node(state: OverallState):
    messages = state.get("messages", [])
    AI_answer = state.get("AI_answer", "")
    action_result = state.get("action_result", [])
    input_text = state.get("input", "")

    # 这里可以调用你的语言模型来生成回答
    answer = f"{AI_answer}"


    color_printer.llm_output(f"AI回答: {answer}")

# 定义查找函数
def find_dict_by_tool(action_result, target_tool):
    for item in action_result:
        if item.get("tool_name") == target_tool:
            return item
    return None

def tool_execution_node(state: OverallState):
    try:
        messages = state.get("messages", [])
        tool_calls = state.get("tool_calls")
        action_result = state.get("action_result", [])

        tool_invocations = [
            ToolInvocation(tool=call["name"], tool_input=call["args"]) for call in tool_calls
        ]

        for invocation in tool_invocations:
            observation = tool_executor.invoke(invocation)
            tool_call_id = {tool_call["name"]: tool_call["id"] for tool_call in tool_calls}.get(invocation.tool)

            action = find_dict_by_tool(action_result, invocation.tool)
            if action:
                # list(action.values())[0]['result']=observation
                action['执行情况'] = observation.get("status")
                action['返回结果'] = observation.get("message")

            print_text = f"执行工具：{invocation.tool},tool_call_id:{tool_call_id}\n输入参数：{invocation.tool_input}\n执行结果：{action}"
            print('tool_execute:',print_text)
            action_result.append(action)

        return {
            "messages":messages,
            "action_result": action_result,
            "tool_calls": None  # ✅ 清空 `tool_calls`，防止无限循环
        }
    except Exception as e:
        return {"error in execute_agent_action": str(e)}


class CustomToolNode:
    def __init__(self, tools, pre_fn=None, post_fn=None):
        self.tool_node = ToolNode(tools=tools)
        self.pre_fn = pre_fn
        self.post_fn = post_fn

    def __call__(self, state: dict):
        if self.pre_fn:
            state = self.pre_fn(state)

        state = self.tool_node.invoke(state)
        if self.post_fn:
            state = self.post_fn(state)
        return state





def router(state:OverallState):
    """根据状态决定下一步"""
    input_text = state.get("input", "").strip().lower()
    tool_calls = state.get("tool_calls", [])

    # 检查是否要退出
    if input_text in ["exit", "end", "quit"]:
        return "exit"

    # 检查是否有工具调用需要执行
    if tool_calls:
        return "execute_tools"

    # 默认返回用户输入节点继续对话
    return "continue_dialog"




graph.add_node("user_input_node",input_node)
graph.add_node("agent_node",AgentNode(config={}))
# graph.add_node("tool_execution_node",tool_execution_node)
graph.add_node("answer_node",answer_node)
graph.add_node("tool_execution_node", CustomToolNode(tools=[get_robot_end_pos_and_ori]))

graph.add_edge(START,"user_input_node")
graph.add_edge("user_input_node","agent_node")
graph.add_conditional_edges("agent_node",router,{"execute_tools": "tool_execution_node","continue_dialog": "answer_node","exit": END,})
graph.add_edge("tool_execution_node","agent_node")
graph.add_edge("answer_node",END)



compiled_graph = graph.compile(checkpointer=memory)

session1_config = {"configurable": {"thread_id": "session-1"}}


if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    try:
        while True:
            result = compiled_graph.invoke({"messages": [],"AI_answer":""},config=session1_config)
            if result.get("input", "").strip().lower() in ["exit", "end", "quit"]:
                print("对话结束。")
                break
    except Exception as e:
        print(f"显示图形时出错: {e}")