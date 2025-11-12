from langchain.tools import tool  # ✅ 直接使用装饰器
import requests
import httpx
from core.task import *
from typing import Dict,Union
import httpx
from core.simulation_request import *

@tool
async def get_robot_end_pos_and_ori(description,robot_id,reference_frame="world"):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - reference_frame (str): 参考系，默认 "world" "world"|"body"|"CNC_C"

    返回:
    - dict: API 响应数据，包含 "status"、"messages":`end_pos` 和 `end_ori`
    """
    url = f"http://localhost:8001/get_robot_end_pos_and_ori"
    try:
        request = GetPosOriRequest(object_id=None, reference_frame=reference_frame)
        async with httpx.AsyncClient() as client:
            response = await client.post(url,json=request.to_dict())
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"[simulation_tools:get_robot_end_pos_and_ori] HTTP Error: {response.status_code}, {response.text}")

    except Exception as e:
        return {"status": "error", "message": str(e)}




@tool
def plan_A2B(description,robot_id,start_pos,start_ori,end_pos,end_ori):
    """
    规划机械臂从点 A 到点 B 的路径。
    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - start_pos (list): 起始位置 [x, y, z]
    - start_ori (list): 起始姿态 [qx, qy, qz, qw]
    - end_pos (list): 目标位置 [x, y, z]
    - end_ori (list): 目标姿态 [qx, qy, qz, qw]
    返回:
    - dict: API 响应数据，包含 `status` 和 `message`
    """

    try:
        result = [{"joint_positions": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "time_from_start": 1.0},
                  {"joint_positions": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7], "time_from_start": 2.0}]
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@tool
async def set_robot_end_pos_and_ori(description, robot_id, pos, ori, reference_frame="world", maxVelocity=1):
    '''
    设置机械臂末端位置和姿态。
    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - pos (list): 目标位置 [x, y, z]
    - ori (list): 目标姿态 [qx, qy, qz, qw]
    - reference_frame (str): 参考系，默认 "world" "world"|"body"|"CNC_C"
    - maxVelocity (float): 最大速度，默认 1
    '''

    url = f"http://localhost:8001/move_robot_to_target"
    try:
        request = PosMoveRequest(
        robot_id=None,
        target_position=pos,
        target_orientation=ori,
        reference_frame=reference_frame,
        maxVelocity=maxVelocity
    )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to set_robot_end_pos_and_ori"}
    except Exception as e:
        print(f"[CustomSimulationEnv:set_robot_tcp_pos_and_ori] Exception: {e}")
        return {"status": "error", "message": str(e)}



using_tools = [get_robot_end_pos_and_ori,set_robot_end_pos_and_ori]