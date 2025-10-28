
from agent.nodes.interactive_graph.state import OverallState
from langchain.schema import HumanMessage
from agent_project_v2.agent.nodes.node_publisher import send_state

def input_node(state: OverallState):
    input_type = state.get("input_type", "debug")
    if input_type == "debug":
        user_input = input("请输入您的问题（输入 'exit' 结束对话）：")
    else:
        user_input = state.get("input", "")
    # messages = state.get("messages", [])
    # messages.append(HumanMessage(content=user_input))
    send_state("user_input_node", {"status": "running", "content": user_input})
    return {"input":user_input,"messages": HumanMessage(content=user_input) }