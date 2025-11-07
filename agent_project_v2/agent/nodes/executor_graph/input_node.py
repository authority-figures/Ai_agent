
from agent.nodes.executor_graph.state import OverallState
from langchain.schema import HumanMessage
from agent.nodes.node_publisher import send_state
from core.task import Task, TaskResponse
from agent.tools.interactive_graph_tools import get_task

async def input_node(state: OverallState):
    input_type = state.get("input_type", "debug")
    task_id = state.get("task_id", "unknown_task")
    task_response = await get_task.ainvoke({"task_id": task_id})

    task = task_response.message

    if task is None:
        return {"input": "", "messages": HumanMessage(content="无法获取任务详情"),"task":None}


    if input_type == "debug":
        user_input = input("请输入您的问题（输入 'exit' 结束对话）：")
    else:
        user_input = state.get("input", "")

    # task_text = Task.from_hdict()
    prompt = f"请你依据任务表的plan内容以及执行情况，开始执行每个step: \n{task}\n"
    return {"input":"","messages": HumanMessage(content=prompt),"task":task}