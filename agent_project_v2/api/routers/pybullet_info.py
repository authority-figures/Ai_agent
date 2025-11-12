# run_pybullet_service.py
import asyncio

import uvicorn

import threading
import time


from fastapi import FastAPI,Request
from pydantic import BaseModel
from execution.simulation.environment import SimulationEnvironment
from execution.simulation.models import *
from core.simulation_request import *

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




@app.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori(request: GetIDRequest):
    """ API: 获取机械臂末端位置 """
    try:
        pos,ori = sim_env.get_object_pos_and_ori(request.robot_id)
        return {"status": "success", "end_pos": pos, "end_ori": ori}
    except Exception as e:
        print("[execution:simulation:api:get_object_pos_and_ori] Error getting object pos and ori:", e)
        return {"status": "error", "message": str(e)}



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


@app.post("/show_tcp_axis")
async def show_tcp_axis(request: dict):
    """ API: 向仿真环境添加物体 """
    try:
        ifshow = request.get("ifshow", True)
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        # 定义回调函数
        def show_tcp():
            sim_env.robot_list[0].show_link_sys(linkIndex=10, lifetime=-1, type=1, name="tcp")

        # 唯一标识符
        callback_id = "show_tcp"

        # 动态添加或移除回调
        if ifshow:
            sim_env.add_simulation_callback(show_tcp, callback_id)
        else:
            sim_env.remove_all_DebugItems()

            sim_env.remove_simulation_callback(callback_id)

        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:show_axis] Error showing axis:", e)
        return {"status": "error", "message": str(e)}

@app.post("/get_robot_end_pos_and_ori")
async def get_robot_end_pos_and_ori(request: GetPosOriRequest):
    """ API: 获取机械臂末端位置 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        if request.reference_frame == "body":
            pos, ori = sim_env.robot_list[0].get_pos_ori_from_ik(tcp_name=None)
        elif request.reference_frame == "world":
            pos, ori = sim_env.robot_list[0].show_link_sys(5,0.1,1)
            # pos, ori = sim_env.get_robot_end_pos_and_ori(sim_env.robot_list[0].id_robot)
        elif request.reference_frame == "CNC_C":
            pos, ori = sim_env.robot_list[0].get_position_relative_to_link(
                bodyA_id=sim_env.robot_list[0].id_robot,
                bodyB_id=sim_env.machine.id_robot,
                linkA_id=5,
                linkB_id=sim_env.machine.turntable_index,
            )
        else:
            return {"status": "error", "message": "No reference frame matched"}

        data = {"pos": tuple(pos), "ori": tuple(ori)}
        return {"status": "success", "message": data}
    except Exception as e:
        print("[execution:simulation:api:get_robot_end_pos_and_ori] Error getting robot end pos and ori:", e)
        return {"status": "error", "message": str(e)}


@app.post("/get_tcp_pos_and_ori")
async def get_tcp_pos_and_ori(request: GetPosOriRequest):
    """ API: 获取机械臂末端位置 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        if request.reference_frame == "body":
            pos, ori = sim_env.robot_list[0].get_pos_ori_from_ik(tcp_name="rolling_tool")
        elif request.reference_frame == "world":
            pos, ori = sim_env.robot_list[0].show_link_sys(10,1,1)
        elif request.reference_frame == "CNC_C":
            pos, ori = sim_env.robot_list[0].get_position_relative_to_link(
                bodyA_id=sim_env.robot_list[0].id_robot,
                bodyB_id=sim_env.machine.id_robot,
                linkA_id=10,
                linkB_id=sim_env.machine.turntable_index,
            )
        else:
            return {"status": "error", "message": "No reference frame matched"}
        data = {"pos": tuple(pos), "ori": tuple(ori)}
        return {"status": "success", "message": data}
    except Exception as e:
        print("[execution:simulation:api:get_tcp_pos_and_ori] Error getting TCP pos and ori:", e)
        return {"status": "error", "message": str(e)}







def start_api_server():
    """ 启动 API 服务器 """
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)

# ===============================================================================
# 机械臂状态发布频道
# ===============================================================================
from fastapi import WebSocket, WebSocketDisconnect

class RobotStateManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_robot_state(self, data: dict):
        """ 向所有连接的客户端发送机械臂状态数据 """
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except WebSocketDisconnect:
                self.active_connections.remove(connection)


robot_state_manager = RobotStateManager()


@app.websocket("/ws/robotstate")
async def websocket_endpoint(websocket: WebSocket):
    """ WebSocket 路由，用于订阅机械臂状态信息 """
    await robot_state_manager.connect(websocket)
    try:
        while True:
            # 接收客户端的消息（如果有）
            await websocket.receive_text()
    except WebSocketDisconnect:
        robot_state_manager.disconnect(websocket)
        print("Client disconnected")


current_task = None
@app.post("/publish_robot_state")
async def publish_robot_state(request: dict):
    """ 用于发布机械臂的状态信息，推送到所有连接的客户端 """
    # 假设你从仿真环境获取机械臂的状态信息
    try:
        global current_task
        on_pub = request.get("on_subscribe", True)
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        async def pub_robot_state():
            while True:
                try:
                    await asyncio.sleep(0.1)
                    joint_states = sim_env.robot_list[0].get_joints_states()
                    robot_state = {
                        "status": "success",
                        "jointstates": joint_states,
                    }
                    await robot_state_manager.send_robot_state(robot_state)
                except asyncio.CancelledError:
                    # Handle the task cancellation gracefully
                    print("Publishing robot state task was cancelled.")
                    break  # Break the loop if the task is cancelled

        # 动态添加或移除回调
        if on_pub:
            # 如果任务已经存在，则先取消它
            if current_task and not current_task.done():
                current_task.cancel()
                print("Previous task cancelled.")

            # 创建并启动新任务
            current_task = asyncio.create_task(pub_robot_state())
            return {"status": "success", "message": "Robot state publishing started"}
        else:
            if current_task and not current_task.done():
                current_task.cancel()  # 取消任务
                await current_task  # 确保任务取消后清理
                return {"status": "success", "message": "Robot state publishing canceled"}
            else:
                return {"status": "error", "message": "No active task to cancel"}


    except Exception as e:
        print("[execution:simulation:api:publish_robot_state] Error publishing robot state:", e)
        return {"status": "error", "message": str(e)}








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
