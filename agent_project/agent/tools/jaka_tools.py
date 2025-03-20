import requests
import json
from langchain.tools import tool  # ✅ 直接使用装饰器
from agent_project.api_server.models.JakaCommands import *


ROBOT_API_URL = "http://127.0.0.1:8000/robotics"

@tool
def power_on_robot():
    """ 调用 API 服务器来启动机器人(真实环境) """
    url = f"{ROBOT_API_URL}/power_on"
    response = requests.post(url)
    return response.json()

@tool
def power_off_robot():
    """ 调用 API 服务器来关闭机器人(真实环境) """
    url = f"{ROBOT_API_URL}/power_off"
    response = requests.post(url)
    return response.json()

@tool
def enable_robot():
    """ 调用 API 服务器来使能机器人(真实环境) """
    url = f"{ROBOT_API_URL}/enable_robot"
    response = requests.post(url)
    return response.json()

@tool
def disable_robot():
    """ 调用 API 服务器来失能机器人(真实环境) """
    url = f"{ROBOT_API_URL}/disable_robot"
    response = requests.post(url)
    return response.json()

@tool
def joint_move(params: JointMoveParams):
    """
    调用 API 服务器来控制机器人关节移动(真实环境)
    参数：包含关节位置、移动模式、速度、加速度、是否阻塞、容差，类型为 JointMoveParams，格式如下：
    {
        "joint_position": list[float],  # 关节位置
        "move_mode": int,optional                       # 移动模式表示关节移动的方式，0 表示绝对移动，1 表示相对移动，默认为 0
        "speed": float,optional                           # 速度(单位：度/秒),默认为 10
        "acc": float,optional                               # 加速度(单位：度/秒^2),默认为 10
        "is_block": bool,optional                        # 是否阻塞,默认为 True
        "tol": float,optional                              # 容差,默认为 0.1
    }

    """
    if not isinstance(params, JointMoveParams):
        raise ValueError("params must be an instance of JointMoveParams")

    url = f"{ROBOT_API_URL}/joint_move"
    response = requests.post(url, json=params.dict())
    return response.json()
