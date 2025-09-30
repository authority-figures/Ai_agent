import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

from langgraph.graph import StateGraph, START, END
from agent_project.agent.nodes import action_node
from agent_project.agent.nodes import agent_node
from agent_project.agent.nodes import user_input_node
from langchain.schema import AgentAction,AgentFinish
from typing import TypedDict,Annotated
from langgraph.graph.message import Messages  # 导入Langchain的Messages类
from agent_project.agent.messages.myMessages import SimpleMessages
import operator
import matplotlib.image as mpimg

# ✅ 1. 定义 `State`，LangGraph 任务的状态信息
class State(TypedDict):
    input: str
    messages: SimpleMessages  # 使用Langchain的Messages类
    action_result: list  # 存储工具调用结果
    tool_calls: list # 存储工具调用

# ✅ 初始化 LangGraph
workflow = StateGraph(State)

# ✅ 添加节点
workflow.add_node("user_input_node",user_input_node)
def return2input(state):
    # 返回空输入
    return {"input":""}
workflow.add_node("clear_input_node",return2input)
workflow.add_node("agent_node",agent_node)
workflow.add_node("action_node",action_node,metadata={"node_type":"action"})

# 路由条件函数 - 决定是继续循环还是结束
def router(state):
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




# ✅ 任务流程
workflow.add_edge(START, "user_input_node")  # 设置起点
workflow.add_edge("user_input_node", "agent_node")  # 设置起点
workflow.add_edge("clear_input_node", "user_input_node")
workflow.add_conditional_edges("agent_node",router,{"execute_tools": "action_node","continue_dialog": "clear_input_node","exit": END,},)


# def should_continue(state):
#     # If the agent outcome is an AgentFinish, then we return `exit` string
#     # This will be used when setting up the graph to define the flow
#     tool_calls = state.get("tool_calls")
#
#
#     if tool_calls:
#         return "continue"  # ✅ 继续执行 `action_node`
#
#     # 🔴 保护机制：如果 `agent_action` 为空，默认终止，防止无限循环
#     return "end"

workflow.add_edge("action_node", "agent_node")  # 循环执行
# ✅ 编译 Graph
graph = workflow.compile()



if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt

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