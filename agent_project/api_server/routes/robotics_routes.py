from fastapi import APIRouter, Depends
from agent_project.api_server.models.JakaCommands import *
from agent_project.api_server.controllers.robotics_controller import *

router = APIRouter()




@router.post("/power_on")
async def power_on_robot_router():
    """
    通过 API 启动机器人
    """
    return await power_on_robot()

@router.post("/power_off")
async def power_off_robot_router():
    """
    通过 API 关闭机器人
    """
    return await power_off_robot()

@router.post("/enable_robot")
async def enable_robot_router():
    """
    通过 API 使能机器人
    """
    return await enable_robot()

@router.post("/disable_robot")
async def disable_robot_router():
    """
    通过 API 失能机器人
    """
    return await disable_robot()



@router.post("/joint_move")
async def joint_move_router(command: JointMoveParams):
    """
    接收 Agent 发送的移动指令，并调用仿真环境执行机械臂移动
    """
    result = await joint_move(command)
    return {"status": "success", "message": result}


