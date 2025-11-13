from langchain.tools import tool  # ✅ 直接使用装饰器
import requests
import httpx
from core.task import *
from typing import Dict,Union


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
async def push_plan(task_id:str,plan:List[PlanStep])-> bool:
    """
    为task制定详细的执行计划。

    参数:
    - task_id (str): 目标任务的id
    - plan (List[PlanStep]): 任务的执行计划

    返回:
    - bool: 是否成功推送计划
    """
    url = f"http://localhost:8000/api/tasks/{task_id}/plan"
    try:
        # 将 plan 转换为 JSON
        plan_data = [step.model_dump() for step in plan]
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=plan_data)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"[plan_graph_tools:push_plan] HTTP Error: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[plan_graph_tools:push_plan] Network error occurred: {e}")
    except Exception as e:
        print(f"[plan_graph_tools:push_plan] Unexpected error occurred: {e}")


@tool
def write_execution_step(id:str,action:str,status:str,log:list[str])-> dict:
    """
    记录任务的执行步骤。
    参数:
    - id (str): 执行步骤的唯一标识符
    - action (str): 执行的具体操作描述
    - status (str): 执行步骤的状态， #只能填写如下四种情况 pending | finished | failed | cancelled
    - log (list[str]): 执行步骤的日志信息列表
    返回:
    - Task: 更新后的任务对象,以标准的json格式返回结果，结构为ExecutionStep 的dict
    """

    step = {
        "id": id,
        "action": action,
        "status": status,
        "log": log
    }

    return step




using_tools = [write_execution_step]