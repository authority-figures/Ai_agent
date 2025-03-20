from fastapi import APIRouter, Depends
from agent_project.api_server.models.commands import *
from agent_project.api_server.controllers.simulation_controller import *

router = APIRouter()



@router.post("/start_simulation")
async def api_start_simulation():
    """ 通过 API 启动仿真环境 """
    return start_simulation()

@router.post("/clear_env")
async def clear_env_route():
    """
    清空仿真环境
    """
    result = await clear_env()
    return {"status": "success", "message": result}

@router.post("/move")
async def move_robot_arm(command: MoveCommand):
    """
    接收 Agent 发送的移动指令，并调用仿真环境执行机械臂移动
    """
    result = await move_arm(command)
    return {"status": "success", "message": result}


@router.post("/load_robot")
async def load_robot_route(command: Load_ObjectCommand):
    """
    接收 Agent 发送的移动指令，并调用仿真环境执行机械臂移动
    """
    result = await load_robot(command)
    return {"status": "success", "message": result}

@router.post("/move_robot_to_target")
async def move_robot_to_target_route(command: TargetMoveRequest):
    """
    接收 Agent 发送的移动指令，并调用仿真环境执行机械臂移动
    """
    result = await move_robot_to_target(command)
    return {"status": "success", "message": result}

@router.post("/get_robot_end_pos_and_ori")
async def get_robot_end_pos_and_ori_route(command: GetIDRequest):
    """
    获取机械臂末端的位置和方向
    """
    result = await get_robot_end_pos_and_ori(command)
    return {"status": "success", "message": result}


@router.post("/create_cube")
async def create_cube_route(command: CreateCubeRequest):
    """
    创建一个立方体
    """
    result = await create_cube(command)
    return {"status": "success", "message": result}


@router.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori_route(command: GetIDRequest):
    """
    获取物体的位置和方向
    """
    result = await get_object_pos_and_ori(command)
    return {"status": "success", "message": result}