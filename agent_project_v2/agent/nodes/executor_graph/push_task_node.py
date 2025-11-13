
from agent.nodes.executor_graph.state import OverallState
from langchain.schema import HumanMessage
from agent.nodes.node_publisher import send_state
from core.task import Task, TaskResponse
from agent.tools.interactive_graph_tools import get_task
from agent.utils import ColorPrinter
import httpx
import time

async def push_task_node(state: OverallState):
    time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    ColorPrinter.debug_normal(f"[push_task_node] |{time_}|进入push_task_node节点")
    task = state.get("task", None)
    if not task:
        return
    task_id = task.task_id

    if state.get("task_finished", False):
        task.status = "success"
    else:
        task.status = "running"

     # 推送任务到后端 API
    url = f"http://localhost:8000/api/tasks/{task_id}/update"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=task.model_dump())
            if response.status_code == 200:
                data = response.json()
                status = data["status"]

                time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                ColorPrinter.debug_normal(f"[push_task_node] |{time_}|离开push_task_node节点")
                if status == "success":
                    return {"task_pushed":True,"task_finished": state.get("task_finished", False)}
                else:
                    return {"task_pushed":False,"task_finished": state.get("task_finished", False)}
            else:
                print("push_task_node", {"status": "error", "content": f"HTTP Error: {response.status_code}, {response.text}"})
    except httpx.RequestError as e:
        print("push_task_node", {"status": "error", "content": f"Network error occurred: {e}"})

