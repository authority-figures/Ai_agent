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



using_tools = [get_robot_end_pos_and_ori,plan_A2B]