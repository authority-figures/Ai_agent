from langchain.tools import tool  # ✅ 直接使用装饰器
import requests
import httpx
from core.task import *
from typing import Dict,Union

@tool
def get_robot_end_pos_and_ori(description,robot_id):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID

    返回:
    - dict: API 响应数据，包含 `status`、`end_pos` 和 `end_ori`
    """

    try:
        result = {"end_pos": [0.5, 0.3, 0.2], "end_ori": [0, 0, 0, 1]}
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool
async def create_task(description,task_name, owner):
    """
    创建一个任务。

    参数:
    - description (str): 用户的原始需求
    - task_name (str): 依据任务描述生成一个简短的任务名称
    - owner (str): "user"|"agent"

    返回:
    - {"status":"...","messgae":{"task_id":"","task_name":""}}: message 包含创建的任务 ID 和任务名称
    """
    url = "http://localhost:8000/api/tasks/create"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params={"owner": owner,"desc":description,"task_name":task_name})
            if response.status_code == 200:
                data = response.json()
                return {"status":data["status"], "message": data["data"]}
            else:
                print(f"[interactive_graph_tools:create_task] HTTP Error: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[interactive_graph_tools:create_task] Network error occurred: {e}")




@tool
async def get_task(task_id,)-> TaskResponse:
    """
    获取目标任务的最新详情。

    参数:
    - task_id (str): 目标任务的id

    返回:
    - {"status":"...","messgae":Task}: message 包含创建的任务 ID 和任务名称
    """
    url = f"http://localhost:8000/api/tasks/{task_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"task_id": task_id})
            if response.status_code == 200:
                data = response.json()
                return TaskResponse(status=data["status"], message=data["message"])
            else:
                print(f"[interactive_graph_tools:create_task] HTTP Error: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[interactive_graph_tools:create_task] Network error occurred: {e}")
    except Exception as e:
        print(f"[interactive_graph_tools:get_task] Unexpected error occurred: {e}")




using_tools = [create_task,get_task]