import asyncio
import aioredis
from fastapi import APIRouter, HTTPException, Depends


from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import Graph, END, StateGraph, START

from agent.utils import ColorPrinter
from langgraph.checkpoint.memory import InMemorySaver
from agent.nodes.executor_graph.state import OverallState
from agent.nodes.executor_graph.agent_node import AgentNode
from agent.nodes.executor_graph.input_node import input_node
from agent.nodes.executor_graph.tool_node import tool_node
from agent.nodes.executor_graph.router import router

memory = InMemorySaver()
color_printer = ColorPrinter()
graph = StateGraph(OverallState)




graph.add_node("user_input_node",input_node)
graph.add_node("agent_node",AgentNode(config={}))
# graph.add_node("tool_execution_node",tool_execution_node)

graph.add_node("tool_execution_node", tool_node)

graph.add_edge(START,"user_input_node")
graph.add_edge("user_input_node","agent_node")
graph.add_conditional_edges("agent_node",router,{"execute_tools": "tool_execution_node","exit": END,})
graph.add_edge("tool_execution_node","agent_node")
# graph.add_edge("answer_node",END)



compiled_graph = graph.compile(checkpointer=memory)

session1_config = {"configurable": {"thread_id": "session-1"}}


if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    try:
        png_data = compiled_graph.get_graph().draw_mermaid_png()
        with open("graph_visualization.jpg", "wb") as f:
            f.write(png_data)
        img = mpimg.imread("graph_visualization.jpg")
        plt.imshow(img)
        plt.axis('off')  # 可选：关闭坐标轴显示
        plt.show()
    except Exception as e:
        print(f"显示图形时出错: {e}")

    try:
        while True:
            result = compiled_graph.invoke({"messages": [],"AI_answer":""},config=session1_config)
            if result.get("input", "").strip().lower() in ["exit", "end", "quit"]:
                print("对话结束。")
                break
    except Exception as e:
        print(f"显示图形时出错: {e}")