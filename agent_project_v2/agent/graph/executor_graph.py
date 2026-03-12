import asyncio
import aioredis
from fastapi import APIRouter, HTTPException, Depends


from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import Graph, END, StateGraph, START

from agent.utils import ColorPrinter
from langgraph.checkpoint.memory import InMemorySaver
from agent.nodes.executor_graph.state import OverallState
from agent.nodes.executor_graph.execute_step_agent_node import AgentNode as execute_step_AgentNode
from agent.nodes.executor_graph.write_step_agent_node import AgentNode as write_step_AgentNode
from agent.nodes.executor_graph.input_node import input_node
from agent.nodes.executor_graph.tool_node import exec_tool_node,write_tool_node
from agent.nodes.executor_graph.router import router_executor, router_writter, router_update_node
from agent.nodes.executor_graph.push_task_node import push_task_node

memory = InMemorySaver()
color_printer = ColorPrinter()
graph = StateGraph(OverallState)




graph.add_node("user_input_node",input_node)
graph.add_node("execute_step_agent",execute_step_AgentNode(config={}))
graph.add_node("write_step_agent",write_step_AgentNode(config={}))
# graph.add_node("tool_execution_node",tool_execution_node)
graph.add_node("exec_tool_node", exec_tool_node)
graph.add_node("write_tool_node", write_tool_node)
graph.add_node("push_task_node", push_task_node)

graph.add_edge(START,"user_input_node")
graph.add_edge("user_input_node","execute_step_agent")
graph.add_conditional_edges("execute_step_agent",router_executor,{"execute_tools": "exec_tool_node","exit": "write_step_agent",})
graph.add_edge("exec_tool_node","write_step_agent")

graph.add_edge("write_tool_node","push_task_node")

graph.add_conditional_edges("write_step_agent",router_writter,{"execute_tools": "write_tool_node","exit": "push_task_node",})
graph.add_conditional_edges("push_task_node",router_update_node,{"continue": "execute_step_agent","exit": END,})
# graph.add_edge("answer_node",END)



compiled_graph = graph.compile(checkpointer=memory)

session1_config = {"configurable": {"thread_id": "session-1"}}


if __name__ == '__main__':

    import io
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    try:
        png_data = compiled_graph.get_graph().draw_mermaid_png()
        with open("exec.jpg", "wb") as f:
            f.write(png_data)
        img = mpimg.imread("exec.jpg")
        plt.imshow(img)
        plt.axis('off')  # 可选：关闭坐标轴显示
        plt.show()

        # png_data = compiled_graph.get_graph().draw_mermaid_png()
        #
        # img = mpimg.imread(io.BytesIO(png_data))  # 直接从内存读，不用先写文件
        #
        # plt.figure(dpi=2000)  # 这行可选：设置显示/保存用的默认dpi
        # plt.imshow(img)
        # plt.axis("off")
        #
        # plt.savefig(
        #     "graph_visualization.png",
        #     dpi=2000,  # 关键：指定dpi
        #     bbox_inches="tight",
        #     pad_inches=0
        # )
        # plt.close()
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