from langgraph.prebuilt import ToolNode
from langchain.tools import Tool
from langgraph.prebuilt.tool_executor import ToolExecutor,ToolInvocation

from langchain_core.messages import ToolMessage
from langgraph.graph.message import Messages  # 导入Langchain的Messages类
from agent_project.agent.messages.myMessages import SimpleMessages
# ✅ 引入所有工具
from agent_project.agent.tools import load_robot,move_robot_to_target,create_cube,clear_env,get_robot_end_pos_and_ori
from agent_project.agent.tools import power_on_robot,power_off_robot,enable_robot,disable_robot,joint_move
from agent_project.agent.utils import ColorPrinter

simulation_tools = [load_robot,move_robot_to_target,create_cube,clear_env,get_robot_end_pos_and_ori]
jaka_tools = [power_on_robot,power_off_robot,enable_robot,disable_robot,joint_move]

tool_executor = ToolExecutor(tools=simulation_tools+jaka_tools)


color_printer = ColorPrinter()


# 定义查找函数
def find_dict_by_tool(action_result, target_tool):
    for item in action_result:
        if item.get("使用工具") == target_tool:
            return item
    return None

def execute_agent_action(state):
    """
    统一执行所有的 `AgentAction`
    """
    try:
        messages = state.get("messages", SimpleMessages())
        tool_calls = state.get("tool_calls")
        action_result = state.get("action_result", [])
        print("tool_calls",tool_calls)

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
            color_printer.tool_execute(print_text)

        return {
            "messages":messages,
            "action_result": action_result,
            "tool_calls": None  # ✅ 清空 `tool_calls`，防止无限循环
        }
    except Exception as e:
        return {"error in execute_agent_action": str(e)}


def action_node(state):

    # ✅ 返回结果
    return execute_agent_action(state)