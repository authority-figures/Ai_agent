
from langgraph.prebuilt import ToolNode, ToolInvocation
from agent.nodes.node_publisher import send_state
from agent.tools.plan_graph_tools import using_tools
import time
from agent.utils import ColorPrinter


class CustomToolNode:
    def __init__(self, tools, pre_fn=None, post_fn=None):
        self.tool_node = ToolNode(tools=tools)
        self.pre_fn = pre_fn
        self.post_fn = post_fn

    async def __call__(self, state: dict):
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[plan_tool_node] |{time_}|进入plan_tool_node节点", color="blue")
        if self.pre_fn:
            state = self.pre_fn(state)

        try:
            # state = self.tool_node.invoke(state)
            state = await self.tool_node.ainvoke(state)

        except Exception as e:
            print(f"Tool execution error: {e}")
            send_state("tool_execution_node", {"status": "error", "content": str(e)})
            raise e

        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[plan_tool_node] |{time_}|离开plan_tool_node节点", color="blue")

        if self.post_fn:
            state = self.post_fn(state)

        # content = state.get("messages", ["none"])[-1].content if state.get("messages") else "none"
        return state



tool_node = CustomToolNode(tools=using_tools)  # 初始化时传入工具列表



