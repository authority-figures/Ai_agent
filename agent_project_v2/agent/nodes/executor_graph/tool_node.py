import json
import time
from langgraph.prebuilt import ToolNode, ToolInvocation
from agent.nodes.node_publisher import send_state
from agent.tools.simulation_tools import using_tools as exec_using_tools
from agent.tools.exec_graph_tools import using_tools as write_using_tools
from agent.nodes.executor_graph.state import OverallState
from core.task import ExecutionStep
from agent.utils import ColorPrinter

class CustomToolNode:
    def __init__(self, tools, pre_fn=None, post_fn=None):
        self.tool_node = ToolNode(tools=tools)
        self.pre_fn = pre_fn
        self.post_fn = post_fn

    async def __call__(self, state: OverallState):
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[Executor tool_node] |{time_}|进入tool_node节点")
        if self.pre_fn:
            state = await self.pre_fn(state)


        # 打印工具调用信息
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        if last_message is not None and getattr(last_message, "tool_calls", None):
            ColorPrinter.debug_normal(f"[Executor tool_node] tool_calls={last_message.tool_calls}")
        # 打印工具调用信息


        try:
            # state = self.tool_node.invoke(state)
            tool_message = await self.tool_node.ainvoke(state)

        except Exception as e:
            print(f"Tool execution error: {e}")
            send_state("tool_execution_node", {"status": "error", "content": str(e)})
            raise e
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[Executor tool_node] |{time_}离开tool_node节点")
        if self.post_fn:
            state["messages"] = state.get("messages", []) + tool_message['messages']
            state = await self.post_fn(state)
            return state

        # content = state.get("messages", ["none"])[-1].content if state.get("messages") else "none"
        return {"messages": tool_message}


async def post_fn_exec(state: dict):
    # 假设任务在 state 中，并且你有 task_data 字段
    task = state.get("task")
    tool_message = state.get("messages", [])[-1] if state.get("messages") else None
    print(f"tool_message in post_fn_exec: {tool_message}")
    if tool_message:
        # 获取 ExecutionStep
        state["exec_tool_messages"] = tool_message
    return state



exec_tool_node = CustomToolNode(tools=exec_using_tools,post_fn=post_fn_exec)  # 初始化时传入工具列表


async def post_fn_write(state: dict):
    # 假设任务在 state 中，并且你有 task_data 字段
    task = state.get("task")
    tool_message = state.get("messages", [])[-1] if state.get("messages") else None
    state["write_tool_messages"] = tool_message
    if tool_message:
        # 获取 ExecutionStep
        execution_step = tool_message.content  # 假设工具返回的内容 str
        # 修正字符串：将单引号替换为双引号，并处理嵌套的列表
        if execution_step:
            execution_step_json = json.loads(execution_step)
            execution_step = ExecutionStep.parse_obj(execution_step_json)

            # 将 ExecutionStep 添加到 task 的 execution 字段
            result = task.update_execution(execution_step)
            if not result:
                raise ValueError("执行了计划外的任务步骤，无法更新任务的 execution 字段。")
            state["task"] = task
    return state



write_tool_node = CustomToolNode(tools=write_using_tools,post_fn=post_fn_write)  # 初始化时传入工具列表


