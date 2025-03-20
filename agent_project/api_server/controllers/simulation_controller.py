import asyncio
import httpx  # 用于发送 HTTP 请求
from agent_project.api_server.models.commands import *
from agent_project.api_server.config import Config  # 引入配置
import os
import subprocess


SIMULATION_RUNNER_PATH = r"F:\python\Ai_agent\agent_project\simulation\simulation_runner.py"

def start_simulation():
    """
    在服务器端启动仿真环境
    这里的做法并不严谨，实际情况应该是在simulation服务器上来启动仿真环境，这里只是为了调试方便
    """
    try:
        subprocess.Popen(["python", SIMULATION_RUNNER_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"status": "success", "message": "Simulation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def clear_env():
    """
    清空仿真环境
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/clear_env",
            )
            return response.json()  # 返回仿真服务器的结果
    except Exception as e:
        return {"error": str(e)}


async def move_arm(command: MoveCommand):
    """
    调用仿真环境控制机械臂移动
    """
    await asyncio.sleep(0.1)  # 模拟异步操作
    return f"Moved arm to {command.target}"



async def load_robot(command: Load_ObjectCommand):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/load_robot",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def move_robot_to_target(command: TargetMoveRequest):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/move_robot_to_target",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def get_robot_end_pos_and_ori(command: GetIDRequest):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/get_robot_end_pos_and_ori",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}




async def create_cube(command: CreateCubeRequest):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/create_cube",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def get_object_pos_and_ori(command: GetIDRequest):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.SIMULATION_SERVER_URL}/get_object_pos_and_ori",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}