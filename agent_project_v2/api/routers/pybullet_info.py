# run_pybullet_service.py
import uvicorn

import threading
import time


from fastapi import FastAPI,Request
from pydantic import BaseModel
from execution.simulation.environment import SimulationEnvironment
from execution.simulation.models import *

# 创建 FastAPI 服务器
app = FastAPI()
sim_env = SimulationEnvironment()


@app.post("/start_simulation")
async def start_simulation():
    """ API: 启动仿真环境 """
    try:
        sim_env.start_simulation()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:start_simulation] Error starting simulation:", e)
        return {"status": "error", "message": str(e)}


@app.post("/stop_simulation")
async def stop_simulation():
    """ API: 停止仿真环境 """
    try:
        sim_env.stop_simulation()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:stop_simulation] Error stopping simulation:", e)
        return {"status": "error", "message": str(e)}


@app.post("/init_env")
async def init_env():
    """ API: 向仿真环境添加物体 """
    sim_env.initialize()
    return {"status": "success"}

@app.post("/load_scene")
async def load_scene():
    """ API: 向仿真环境添加物体 """
    try:
        sim_env.load_scene()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:load_scene] Error loading scene:", e)
        return {"status": "error", "message": str(e)}


class ShowAxisRequest(BaseModel):
    ifshow: bool
@app.post("/show_axis")
async def show_axis(request: dict):
    """ API: 向仿真环境添加物体 """
    try:
        ifshow = request.get("ifshow", True)
        sim_env.show_axis(ifshow=ifshow)
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:show_axis] Error showing axis:", e)
        return {"status": "error", "message": str(e)}


@app.post("/clear_env")
async def clear_env():
    """ API: 清理仿真环境中的物体 """
    try:
        sim_env.clear_env()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:clear_env] Error clearing environment:", e)
        return {"status": "error", "message": str(e)}

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









def run_pybullet_service():
    """ 启动PyBullet仿真服务 """
    # simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    # simulation_thread.start()
    # sim_env.initialize()
    uvicorn.run(app, host="127.0.0.1", port=8001,
                reload=False,
                log_level="info",
                loop="asyncio",
                )  # 设置为8001端口运行

if __name__ == "__main__":
    run_pybullet_service()
