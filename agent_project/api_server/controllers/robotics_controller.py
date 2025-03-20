import asyncio
import httpx  # 用于发送 HTTP 请求
from agent_project.api_server.models.JakaCommands import *
from agent_project.api_server.config import Config  # 引入配置
import os
import subprocess


async def joint_move(command: JointMoveParams):
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            data = command.dict()
            response = await client.post(
                f"{Config.ROBOT_SERVER_URL}/joint_move",
                json=data,
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def enable_robot():
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{Config.ROBOT_SERVER_URL}/enable_robot",
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def disable_robot():
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{Config.ROBOT_SERVER_URL}/disable_robot",
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def power_on_robot():
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{Config.ROBOT_SERVER_URL}/power_on",
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

async def power_off_robot():
    """
    发送请求到外部仿真服务器（独立进程运行的 PyBullet 环境）
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{Config.ROBOT_SERVER_URL}/power_off",
            )
            return response.json()  # 返回仿真服务器的结果
        except Exception as e:
            return {"error": str(e)}

