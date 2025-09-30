
from agent_project.agent.messages.myMessages import SimpleMessages


def user_input_node(state):
    """获取用户输入并处理"""
    user_input = state.get("input", "")
    if user_input == "":
        user_input = input("请输入新的指令或退出这轮对话:")

    # 将用户输入添加到消息历史
    messages = state.get("messages", SimpleMessages())
    # messages = messages.add("human", user_input)
    return {
        "input": user_input,
        "messages": messages,
        # 可以在这里重置某些临时状态
        "tool_calls": [],
        "action_result": []
    }