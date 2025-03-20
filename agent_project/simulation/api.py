from fastapi import FastAPI
from pydantic import BaseModel
from agent_project.simulation.environment import SimulationEnvironment
from agent_project.simulation.models import *

# 创建 FastAPI 服务器
app = FastAPI()
sim_env = SimulationEnvironment()



@app.post("/init_env")
async def init_env():
    """ API: 向仿真环境添加物体 """
    sim_env.initialize()
    return {"status": "success"}

@app.post("/clear_env")
async def clear_env():
    """ API: 向仿真环境添加物体 """
    sim_env.clear_env()
    return {"status": "success"}

@app.post("/add_object")
async def add_object(request: LoadObjectRequest):
    """ API: 向仿真环境添加物体 """
    obj_id = sim_env.add_object(request.urdf_path, request.basePosition,request.baseOrientation,request.useFixedBase)
    return {"status": "success", "object_id": obj_id}

@app.post("/load_robot")
async def load_robot(request: LoadObjectRequest):
    """ API: 加载机械臂 """
    robot_id = sim_env.load_robot(request.urdf_path, request.basePosition,request.baseOrientation,request.useFixedBase)
    return {"status": "success", "robot_id": robot_id}


@app.post("/get_robot_end_pos_and_ori")
async def get_robot_end_pos_and_ori(request: GetIDRequest):
    """ API: 获取机械臂末端位置 """
    pos,ori = sim_env.get_robot_end_pos_and_ori(request.robot_id)
    return {"status": "success", "end_pos": pos, "end_ori": ori}

@app.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori(request: GetIDRequest):
    """ API: 获取机械臂末端位置 """
    pos,ori = sim_env.get_object_pos_and_ori(request.robot_id)
    return {"status": "success", "end_pos": pos, "end_ori": ori}



@app.post("/move_robot_to_target")
async def move_robot_to_target(request: TargetMoveRequest):
    """ API: 让机械臂运动 """
    response = sim_env.move_robot_to_target(request.robot_id,request.target_position,request.target_orientation,request.maxVelocity)
    if response == "No robot loaded":
        return {"status": "error", "message": response}
    elif response == "IK failed":
        return {"status": "error", "message": response}
    elif response == "Robot moved failed":
        return {"status": "error", "message": response}
    else:

        return {"status": "success", "message": response}


@app.post("/create_cube")
async def create_cube(request: CreateCubeRequest):
    """ API: 创建立方体 """
    cube_id = sim_env.create_cube(request.pos, request.ori, request.half_extents, request.mass, request.color)
    return {"status": "success", "cube_id": cube_id}

@app.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori(request: GetIDRequest):
    """ API: 获取物体位置和朝向 """
    pos, ori = sim_env.get_object_pos_and_ori(request.robot_id)
    return {"status": "success", "pos": pos, "ori": ori}


def start_api_server():
    """ 启动 API 服务器 """
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
