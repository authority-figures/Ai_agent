
from .state import OverallState



def router(state:OverallState):
    """根据状态决定下一步"""
    input_text = state.get("input", "").strip().lower()
    tool_calls = state.get("tool_calls", [])

    # # 检查是否要退出
    # if input_text in ["exit", "end", "quit"]:
    #     return "exit"

    # 检查是否有工具调用需要执行
    if tool_calls:
        return "execute_tools"
    else:
        return "exit"

    # 默认返回用户输入节点继续对话
    # return "continue_dialog"