

from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent.llm import chatGPT_llm

from agent.nodes.plan_graph.state import OverallState
from agent.tools.plan_graph_tools import using_tools
from agent.tools.simulation_tools import using_tools as simulation_tools
import time
from agent.utils import ColorPrinter

def render_tool_info_as_text(tools) -> str:
    lines = []
    for i, tool in enumerate(tools, 1):
        name = getattr(tool, "name", tool.__class__.__name__)
        desc = getattr(tool, "description", "无描述")
        lines.append(f"{i}. 工具名: {name}\n   功能: {desc}")
    return "\n\n".join(lines)

llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
llm_with_tools = llm.bind_tools(using_tools)

tool_text = render_tool_info_as_text(simulation_tools)

system_prompt = f"""
你是一个AI助理，负责依据传入的任务来制定执行计划。
请你仔细阅读 description 字段来制定 plan。

例如：
当任务为对区域0进行滚压强化时，该计划应该分为以下步骤：
1.获取区域0的路径点信息，包括起始点关节角；
2.使用规划工具规划出从当前点到滚压起始点的插入路径点(依赖step1的路径点信息)；
3.执行规划的插入路径。(依赖step2的路径点信息)；
4.执行滚压路径(依赖step1的路径点信息)。

注意你在制定计划时,可以在规划步骤加入推荐使用的工具,但你不需要使用它们,你只需要知道这些工具是你制定的计划中可能会使用的。

下面这些是“其他 agent 在执行阶段可使用的工具列表”。
你只能把它们当作能力参考，用于制定计划；
你只需要根据这些工具能力，规划出合理的步骤。

可用工具能力如下：
{tool_text}
"""
# system_prompt = ("你是一个AI助理,负责依据传入的任务来制定执行计划,请你仔细阅读description字段来制定plan,例如，当任务为移动机械臂到目标点（1，1，1），姿态为（0，0，0，1）。则应该分为1.获取机械臂当前位置；2.使用规划工具规划出当前点到目标点的路径点；3.执行该路径\n"
#                  "你会看到有些用于执行的工具，但你需要记住，你不要使用它，你只需要知道这些工具是你制定的计划中可能会使用的")

class AgentNode:
    def __init__(self,config):
        self.config = config

    async def __call__(self, state: OverallState):
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[plan_agent_node] |{time_}|进入plan_agent_node节点", color="blue")
        messages = state.get("messages", [])
        action_result = state.get("action_result", [])
        system_message = SystemMessage(content=system_prompt)
        message_history = [system_message] + messages

        llm_output = await llm_with_tools.ainvoke(message_history)


        messages.append(llm_output)

        tool_calls, current_action_result = self.toolcall_parsing(llm_output)

        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[plan_agent_node] |{time_}|离开plan_agent_node节点", color="blue")

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






if __name__ == '__main__':
    print(system_prompt)