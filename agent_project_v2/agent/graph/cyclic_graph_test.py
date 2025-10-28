import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

from langgraph.graph import StateGraph, START, END
from langchain.schema import AgentAction,AgentFinish
from typing import TypedDict,Annotated
from langgraph.graph.message import Messages  # 导入Langchain的Messages类
import operator
import matplotlib.image as mpimg
from agent_project_v2.agent.llm import chatGPT_llm
from agent_project_v2.agent.nodes.node_publisher import send_state
from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent_project.agent.utils import *
from langgraph.constants import Send




# 初始化 LLM（使用 OpenAI API 或其他 LLM）
llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
color_printer = ColorPrinter()
class SimpleMessages:
    def __init__(self):
        self.history = []

    def add(self, role, content):
        self.history.append((role, content))
        return self  # 允许链式调用

def agent_node(state):
    """
    统一执行所有的 `AgentAction`
    """
    try:
        print("state",state)
        send_state("agent_node",{"status":"running","content":state["input"]})

        messages = state.get("messages", SimpleMessages())
        input_text = state.get("input", "")
        action_result = state.get("action_result", [])

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        system_message = SystemMessage(content="你是一个AI助理,请回答用户的问题\n")
        # 将Message.history的内容转化为llm可以invoke的格式化内容
        message_history = [system_message]
        for role, content in messages.history:
            if role == "human":
                message_history.append(HumanMessage(content=content))
            elif role == "assistant":
                message_history.append(AIMessage(content=content))
            elif role == "system":
                message_history.append(SystemMessage(content=content))

        message_history.append(HumanMessage(content=input_text))  # 将当前任务添加到消息末尾
        # ----------------------------------------------------------------------------------
        llm_output = llm.invoke(message_history)
        messages.add("human", input_text)
        messages.add("assistant", llm_output.content)


        color_printer.llm_output(llm_output.content)
        return {"messages": messages}
    except Exception as e:
        return {"error in generate_agent_action": str(e)}


def input_node(state):
    user_input = input("请输入您的问题（输入 'exit' 结束对话）：")
    return {"input": user_input,"count":0}

def print_state_node(state):
    count = state.get("count", 0)
    color_printer.print(f"[print_state_node] 当前计数值为: {count}",color="white")

def scheduler_node(state):
    count = state.get("count", 0)
    color_printer.print(f"[scheduler_node] 当前计数值为: {count}",color="white")
    return [
        Send("add1_node", state),
        Send("add10_node", state),
    ]


def add1_node(state):
    count = state.get("count", 0)
    color_printer.print(f"[add1_node] 当前计数值为: {count}",color="blue")
    return {"count": 1}


def add10_node(state):
    count = state.get("count", 0)

    color_printer.print(f"[add10_node] 当前计数值为: {count}",color="green")
    return {"count": 10}

def middle_node(state):
    count = state.get("count", -1)
    color_printer.print(f"[middle_node] 当前计数值为: {count}",color="blue")

def show_node1(state):
    count = state.get("count", 0)
    color_printer.print(f"[show_node1] 当前计数值为: {count}",color="green")

def show_node2(state):
    count = state.get("count", 0)
    color_printer.print(f"[show_node2] 当前计数值为: {count}",color="green")

def show_node3(state):
    count = state.get("count", 0)
    color_printer.print(f"[show_node3] 当前计数值为: {count}",color="green")

def router(state):
    """根据状态决定下一步"""
    count = state.get("count", 0)

    # 根据 count 决定下一步
    if count < 0:
        return "End"
    else:
        print(f"router: count={count}, continuing...")
        return "Continue"


def hanging_node(state):
    """一个不会结束的节点"""
    count = state.get("count", 0)
    color_printer.print(f"[hanging_node] 当前计数值为: {count}", color="green")
    pass


class State(TypedDict):
    input: str
    messages: SimpleMessages  # 使用Langchain的Messages类
    action_result: list  # 存储工具调用结果
    tool_calls: list # 存储工具调用
    count: Annotated[int, operator.add]  # 用于计数的状态变量

# ✅ 初始化 LangGraph
workflow = StateGraph(State)

# ✅ 添加节点
workflow.add_node("user_input_node",input_node)
workflow.add_node("print_state_node",print_state_node)

workflow.add_node("add1_node",add1_node)
workflow.add_node("add10_node",add10_node)
workflow.add_node("middle_node",middle_node)
workflow.add_node("show_node1",show_node1)
workflow.add_node("show_node2",show_node2)
workflow.add_node("show_node3",show_node3)
workflow.add_node("hanging_node",hanging_node)


workflow.add_edge(START, "print_state_node")  # 设置起点


workflow.add_edge("print_state_node", "add10_node")
workflow.add_edge("print_state_node", "user_input_node")  # 设置起点
workflow.add_edge("user_input_node", "add1_node")
workflow.add_edge("add1_node", "middle_node")
workflow.add_conditional_edges("middle_node",router,{"Continue": "user_input_node","End": END})
workflow.add_edge("add10_node", "show_node1")
workflow.add_edge("show_node1", "show_node2")
workflow.add_edge("show_node2", "show_node3")
workflow.add_edge("show_node3", "hanging_node")
# workflow.add_edge("hanging_node", "show_node1")
workflow.add_conditional_edges("hanging_node",router,{"Continue": "show_node1","End": END})

# ✅ 编译 Graph
graph = workflow.compile()

if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt

    result = graph.invoke({
        "input": "0",
        "messages": SimpleMessages(),
    })

    print("\n🔹 LangGraph 执行结果：", result)

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open("graph_visualization.jpg", "wb") as f:
            f.write(png_data)
        img = mpimg.imread("graph_visualization.jpg")
        plt.imshow(img)
        plt.axis('off')  # 可选：关闭坐标轴显示
        plt.show()
    except Exception as e:
        print(f"显示图形时出错: {e}")