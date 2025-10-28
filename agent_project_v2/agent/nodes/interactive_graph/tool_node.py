
from langgraph.prebuilt import ToolNode, ToolInvocation
from agent_project_v2.agent.nodes.node_publisher import send_state


class CustomToolNode:
    def __init__(self, tools, pre_fn=None, post_fn=None):
        self.tool_node = ToolNode(tools=tools)
        self.pre_fn = pre_fn
        self.post_fn = post_fn

    def __call__(self, state: dict):
        if self.pre_fn:
            state = self.pre_fn(state)

        state = self.tool_node.invoke(state)

        if self.post_fn:
            state = self.post_fn(state)

        send_state("tool_execution_node", {"status": "running", "content": str(state.get("messages", ["none"])[-1])})
        return state



