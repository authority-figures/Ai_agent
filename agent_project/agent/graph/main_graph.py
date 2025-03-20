import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

from langgraph.graph import StateGraph, START, END
from agent_project.agent.nodes import action_node
from agent_project.agent.nodes import agent_node
from typing import TypedDict,Annotated,Optional,List
from langgraph.graph.message import Messages,MessagesState    # 导入Langchain的Messages类
from agent_project.agent.messages.myMessages import SimpleMessages
import operator



# ✅ 1. 定义 `State`，LangGraph 任务的状态信息
class State(TypedDict):
    input: str
    messages: SimpleMessages  # 使用Langchain的Messages类    agent_action: AgentAction | None
    action_result: Annotated[list, operator.add]
    tool_calls: Optional[List]   # 存储工具调用

# ✅ 初始化 LangGraph
workflow = StateGraph(State)

# ✅ 添加节点
workflow.add_node("agent_node",agent_node)
workflow.add_node("action_node",action_node)


# ✅ 任务流程
workflow.add_edge(START, "agent_node")  # 设置起点
def should_continue(state):
    # If the agent outcome is an AgentFinish, then we return `exit` string
    # This will be used when setting up the graph to define the flow
    tool_calls = state.get("tool_calls")


    if tool_calls:
        return "continue"  # ✅ 继续执行 `action_node`

    # 🔴 保护机制：如果 `agent_action` 为空，默认终止，防止无限循环
    return "end"
workflow.add_conditional_edges("agent_node",should_continue,{"continue": "action_node","end": END,},)
workflow.add_edge("action_node", "agent_node")  # 循环执行
# ✅ 编译 Graph
graph = workflow.compile()


if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        img = plt.imread(io.BytesIO(png_data))
        plt.imshow(img)
        plt.axis('off')  # 可选：关闭坐标轴显示
        plt.show()
    except Exception as e:
        print(f"显示图形时出错: {e}")