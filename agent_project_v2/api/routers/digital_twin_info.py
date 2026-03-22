# run_pybullet_service.py
import asyncio
import json
import uvicorn
import numpy as np
from fastapi import FastAPI,Request
from execution.simulation.environment import SimulationEnvironment
from execution.digital_twin.digital_twin_env import DigitalTwinEnv
from execution.simulation.models import *
from core.simulation_request import *
import websockets



# 创建 FastAPI 服务器
app = FastAPI()
DT_env = DigitalTwinEnv(options="MyPyBulletSimulation_")
# DT_env.initialize()
print("DT_env physicsClientId:", DT_env.physics_client)


async def listen_for_robot_status():
    # 用于监听来自机械臂的状态，并将状态设置到DT环境的机械臂当中
    uri = "ws://127.0.0.1:8002/ws/robot_status"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            # 将数据存储到 DigitalTwinEnv 中的 _last_robot_status
            if data["status"] == "ok":
                # 假设数据格式为 {'joint_positions': [...] }
                DT_env._last_robot_status = data["data"]


# 启动监听任务
@app.post("/start_listening_robot_status")
async def start_listening_robot_status():
    """ API: 启动监听机械臂状态 """
    try:
        await asyncio.create_task(listen_for_robot_status())
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:start_listening_robot_status] Error starting listening:", e)
        return {"status": "error", "message": str(e)}


@app.post("/start_simulation")
async def start_simulation():
    """ API: 启动仿真环境 """
    try:
        DT_env.start_simulation()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:start_simulation] Error starting simulation:", e)
        return {"status": "error", "message": str(e)}


@app.post("/stop_simulation")
async def stop_simulation():
    """ API: 停止仿真环境 """
    try:
        DT_env.stop_simulation()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:stop_simulation] Error stopping simulation:", e)
        return {"status": "error", "message": str(e)}


@app.post("/init_env")
async def init_env():
    """ API: 向仿真环境添加物体 """
    DT_env.initialize()
    return {"status": "success"}

@app.post("/load_scene")
async def load_scene():
    """ API: 向仿真环境添加物体 """
    try:
        DT_env.load_scene()
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
        DT_env.show_axis(ifshow=ifshow)
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:show_axis] Error showing axis:", e)
        return {"status": "error", "message": str(e)}


@app.post("/clear_env")
async def clear_env():
    """ API: 清理仿真环境中的物体 """
    try:
        DT_env.clear_env()
        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:clear_env] Error clearing environment:", e)
        return {"status": "error", "message": str(e)}

@app.post("/add_object")
async def add_object(request: LoadObjectRequest):
    """ API: 向仿真环境添加物体 """
    obj_id = DT_env.add_object(request.urdf_path, request.basePosition,request.baseOrientation,request.useFixedBase)
    return {"status": "success", "object_id": obj_id}

@app.post("/load_robot")
async def load_robot(request: LoadObjectRequest):
    """ API: 加载机械臂 """
    robot_id = DT_env.load_robot(request.urdf_path, request.basePosition,request.baseOrientation,request.useFixedBase)
    return {"status": "success", "robot_id": robot_id}




@app.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori(request: GetIDRequest):
    """ API: 获取机械臂末端位置 """
    try:
        pos,ori = DT_env.get_object_pos_and_ori(request.robot_id)
        return {"status": "success", "end_pos": pos, "end_ori": ori}
    except Exception as e:
        print("[execution:simulation:api:get_object_pos_and_ori] Error getting object pos and ori:", e)
        return {"status": "error", "message": str(e)}

@app.post("/get_robot_joints_state")
async def get_robot_joints_state():
    """ API: 获取机械臂末端位置 """
    try:
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        joints = DT_env.robot_list[0].get_joints_states()
        return {"status": "success", "joints_state": joints}
    except Exception as e:
        print("[execution:simulation:api:get_object_pos_and_ori] Error getting object pos and ori:", e)
        return {"status": "error", "message": str(e)}



@app.post("/move_robot_to_target")
async def move_robot_to_target(request: PosMoveRequest):
    """ API: 让机械臂运动 """
    try:
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        robot_id = DT_env.robot_list[0].id_robot

        if request.reference_frame == "body":
            pre_inverse_mode = DT_env.robot_list[0].inverse_mode
            DT_env.robot_list[0].inverse_mode = "body_sys"
            joints_value = DT_env.robot_list[0].get_state_from_ik(request.target_position,request.target_orientation,tcp_name=None)
            DT_env.robot_list[0].joint_move_once(joints_value, maxVelocity=request.maxVelocity)
            DT_env.robot_list[0].inverse_mode = pre_inverse_mode
        elif request.reference_frame == "world":
            # response = DT_env.move_robot_to_target(robot_id,request.target_position,request.target_orientation,request.maxVelocity)
            pre_inverse_mode = DT_env.robot_list[0].inverse_mode
            DT_env.robot_list[0].inverse_mode = "world_sys"
            joints_value = DT_env.robot_list[0].get_state_from_ik(request.target_position, request.target_orientation,
                                                                   tcp_name=None)
            DT_env.robot_list[0].joint_move_once(joints_value, maxVelocity=request.maxVelocity)
            DT_env.robot_list[0].inverse_mode = pre_inverse_mode
        elif request.reference_frame == "CNC_C":
            T_world2robot = DT_env.rm_sys.T_robot2world.copy()
            T_c2world = DT_env.robot_list[0].pos_to_matrix([0,0,-DT_env.machine.C_in_sys0],[0,0,0,1])
            T_c2target = DT_env.robot_list[0].pos_to_matrix(request.target_position,request.target_orientation)
            T_robot2target = np.linalg.inv(T_world2robot) @ np.linalg.inv(T_c2world) @ T_c2target
            pos, ori = DT_env.robot_list[0].matrix_to_pos(T_robot2target)
            pre_inverse_mode = DT_env.robot_list[0].inverse_mode
            DT_env.robot_list[0].inverse_mode = "body_sys"
            joints_value = DT_env.robot_list[0].get_state_from_ik(pos, ori,
                                                                   tcp_name=None)
            DT_env.robot_list[0].joint_move_once(joints_value, maxVelocity=request.maxVelocity)
            DT_env.robot_list[0].inverse_mode = pre_inverse_mode
        else:
            return {"status": "error", "message": "No reference frame matched"}

        return {"status": "success", "message": "Robot moved to target"}

    except Exception as e:
        print("[execution:simulation:api:move_robot_to_target] Error moving robot to target:", e)
        return {"status": "error", "message": str(e)}


@app.post("/create_cube")
async def create_cube(request: CreateCubeRequest):
    """ API: 创建立方体 """
    cube_id = DT_env.create_cube(request.pos, request.ori, request.half_extents, request.mass, request.color)
    return {"status": "success", "cube_id": cube_id}

@app.post("/get_object_pos_and_ori")
async def get_object_pos_and_ori(request: GetIDRequest):
    """ API: 获取物体位置和朝向 """
    pos, ori = DT_env.get_object_pos_and_ori(request.robot_id)
    return {"status": "success", "pos": pos, "ori": ori}


@app.post("/show_tcp_axis")
async def show_tcp_axis(request: dict):
    """ API: 向仿真环境添加物体 """
    try:
        ifshow = request.get("ifshow", True)
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        # 定义回调函数
        def show_tcp():
            DT_env.robot_list[0].show_link_sys(linkIndex=10, lifetime=-1, type=1, name="tcp")

        # 唯一标识符
        callback_id = "show_tcp"

        # 动态添加或移除回调
        if ifshow:
            DT_env.add_simulation_callback(show_tcp, callback_id)
        else:
            DT_env.remove_all_DebugItems()

            DT_env.remove_simulation_callback(callback_id)

        return {"status": "success"}
    except Exception as e:
        print("[execution:simulation:api:show_axis] Error showing axis:", e)
        return {"status": "error", "message": str(e)}

@app.post("/get_robot_end_pos_and_ori")
async def get_robot_end_pos_and_ori(request: GetPosOriRequest):
    """ API: 获取机械臂末端位置 """
    try:
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        if request.reference_frame == "body":
            pos, ori = DT_env.robot_list[0].get_pos_ori_from_ik(tcp_name=None)
        elif request.reference_frame == "world":
            pos, ori = DT_env.robot_list[0].show_link_sys(5,0.1,1)
            # pos, ori = DT_env.get_robot_end_pos_and_ori(DT_env.robot_list[0].id_robot)
        elif request.reference_frame == "CNC_C":
            pos, ori = DT_env.robot_list[0].get_position_relative_to_link(
                bodyA_id=DT_env.robot_list[0].id_robot,
                bodyB_id=DT_env.machine.id_robot,
                linkA_id=5,
                linkB_id=DT_env.machine.turntable_index,
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
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        if request.reference_frame == "body":
            pos, ori = DT_env.robot_list[0].get_pos_ori_from_ik(tcp_name="rolling_tool")
        elif request.reference_frame == "world":
            pos, ori = DT_env.robot_list[0].show_link_sys(10,1,1)
        elif request.reference_frame == "CNC_C":
            pos, ori = DT_env.robot_list[0].get_position_relative_to_link(
                bodyA_id=DT_env.robot_list[0].id_robot,
                bodyB_id=DT_env.machine.id_robot,
                linkA_id=10,
                linkB_id=DT_env.machine.turntable_index,
            )
        else:
            return {"status": "error", "message": "No reference frame matched"}
        data = {"pos": tuple(pos), "ori": tuple(ori)}
        return {"status": "success", "message": data}
    except Exception as e:
        print("[execution:simulation:api:get_tcp_pos_and_ori] Error getting TCP pos and ori:", e)
        return {"status": "error", "message": str(e)}



def _normalize_machine_axis_values(payload):
    if isinstance(payload, dict):
        if "axis_values" in payload:
            values = payload["axis_values"]
        else:
            values = [payload.get(axis) for axis in ["A", "C", "X", "Y", "Z"]]
    elif isinstance(payload, list):
        values = payload
    else:
        raise ValueError("Unsupported machine axis payload type")

    if len(values) != 5:
        raise ValueError("Machine axis values must contain exactly 5 numbers (A, C, X, Y, Z)")
    return [float(value) for value in values]


def _apply_dt_machine_axis_values(axis_values):
    if not hasattr(DT_env, "machine") or DT_env.machine is None:
        raise ValueError("No machine loaded")
    DT_env.machine.set_joints_states(axis_values)
    return axis_values


@app.post("/get_machine_axis_state")
async def get_machine_axis_state():
    """API: 获取数字孪生中的机床 ACXYZ 状态。"""
    try:
        if not hasattr(DT_env, "machine") or DT_env.machine is None:
            return {"status": "error", "message": "No machine loaded"}
        axis_values = DT_env.machine.get_joints_states()
        return {
            "status": "success",
            "axis_labels": ["A", "C", "X", "Y", "Z"],
            "axis_values": list(axis_values),
        }
    except Exception as e:
        print("[execution:digital_twin:api:get_machine_axis_state] Error getting machine axis state:", e)
        return {"status": "error", "message": str(e)}


@app.post("/update_machine_axis_state")
async def update_machine_axis_state(request: MachineAxisRequest):
    """API: 更新数字孪生环境中的机床 ACXYZ 状态。"""
    try:
        axis_values = _apply_dt_machine_axis_values(_normalize_machine_axis_values(request.target_axis_values))
        return {
            "status": "success",
            "message": "Digital twin machine axis updated",
            "axis_labels": ["A", "C", "X", "Y", "Z"],
            "axis_values": list(axis_values),
        }
    except Exception as e:
        print("[execution:digital_twin:api:update_machine_axis_state] Error updating machine axis state:", e)
        return {"status": "error", "message": str(e)}


machine_axis_tcp_server = None
machine_axis_tcp_server_endpoint = {"host": "127.0.0.1", "port": 9101}


async def _handle_machine_axis_tcp_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"[digital_twin_info] Machine axis TCP client connected: {addr}")
    try:
        while True:
            raw_data = await reader.readline()
            if not raw_data:
                break
            message = raw_data.decode("utf-8").strip()
            if not message:
                continue
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = [value.strip() for value in message.split(",") if value.strip()]

            try:
                axis_values = _apply_dt_machine_axis_values(_normalize_machine_axis_values(payload))
                response = {
                    "status": "success",
                    "axis_labels": ["A", "C", "X", "Y", "Z"],
                    "axis_values": list(axis_values),
                }
            except Exception as exc:
                response = {"status": "error", "message": str(exc)}

            writer.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[digital_twin_info] Machine axis TCP client disconnected: {addr}")


@app.post("/start_machine_axis_tcp_server")
async def start_machine_axis_tcp_server(request: dict | None = None):
    """API: 启动机床轴信息 TCP 接收服务。"""
    try:
        global machine_axis_tcp_server
        request = request or {}
        host = request.get("host", machine_axis_tcp_server_endpoint["host"])
        port = int(request.get("port", machine_axis_tcp_server_endpoint["port"]))

        if machine_axis_tcp_server is not None:
            return {
                "status": "success",
                "message": "Machine axis TCP server already running",
                "host": machine_axis_tcp_server_endpoint["host"],
                "port": machine_axis_tcp_server_endpoint["port"],
            }

        machine_axis_tcp_server = await asyncio.start_server(_handle_machine_axis_tcp_client, host, port)
        machine_axis_tcp_server_endpoint["host"] = host
        machine_axis_tcp_server_endpoint["port"] = port
        return {"status": "success", "message": "Machine axis TCP server started", "host": host, "port": port}
    except Exception as e:
        print("[execution:digital_twin:api:start_machine_axis_tcp_server] Error starting machine axis TCP server:", e)
        return {"status": "error", "message": str(e)}


@app.post("/stop_machine_axis_tcp_server")
async def stop_machine_axis_tcp_server():
    """API: 停止机床轴信息 TCP 接收服务。"""
    try:
        global machine_axis_tcp_server
        if machine_axis_tcp_server is None:
            return {"status": "error", "message": "Machine axis TCP server is not running"}
        machine_axis_tcp_server.close()
        await machine_axis_tcp_server.wait_closed()
        machine_axis_tcp_server = None
        return {"status": "success", "message": "Machine axis TCP server stopped"}
    except Exception as e:
        print("[execution:digital_twin:api:stop_machine_axis_tcp_server] Error stopping machine axis TCP server:", e)
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
        if len(DT_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        async def pub_robot_state():
            while True:
                try:
                    await asyncio.sleep(0.1)
                    joint_states = DT_env.robot_list[0].get_joints_states()
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








def run_digital_twin_service():
    """ 启动PyBullet仿真服务 """
    # simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    # simulation_thread.start()
    # DT_env.initialize()
    uvicorn.run(app, host="127.0.0.1", port=8003,
                reload=False,
                log_level="info",
                loop="asyncio",
                )  # 设置为8001端口运行


def run_digital_twin_service_byhand():
    """ 启动PyBullet仿真服务 """
    # simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    # simulation_thread.start()
    DT_env.initialize()
    uvicorn.run(app, host="127.0.0.1", port=8004,
                reload=False,
                log_level="info",
                loop="asyncio",
                )  # 设置为8001端口运行


if __name__ == "__main__":
    run_digital_twin_service_byhand()
