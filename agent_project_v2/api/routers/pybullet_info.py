# run_pybullet_service.py
import asyncio

import uvicorn
import numpy as np
from fastapi import FastAPI,Request
from execution.simulation.environment import SimulationEnvironment
from execution.simulation.models import *
from core.simulation_request import *
import re
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# 创建 FastAPI 服务器
app = FastAPI()
sim_env = SimulationEnvironment(options="MyPyBulletSimulation_")
# sim_env.initialize()  # 不能提前启动
print("sim_env physicsClientId:", sim_env.physics_client)

PLANNED_PATH_DIR = Path(__file__).resolve().parents[2] / "runtime" / "planned_paths"


def _ensure_planned_path_dir() -> Path:
    PLANNED_PATH_DIR.mkdir(parents=True, exist_ok=True)
    return PLANNED_PATH_DIR


def _save_planned_path(planner_name: str, start_joints, target_joints, path):
    path_id = f"path_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    payload = {
        "path_id": path_id,
        "planner_name": planner_name,
        "start_joints": start_joints,
        "target_joints": target_joints,
        "waypoint_count": len(path),
        "path": path,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    path_file = _ensure_planned_path_dir() / f"{path_id}.json"
    path_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path_id, path_file


def _load_planned_path(path_id: str):
    path_file = _ensure_planned_path_dir() / f"{path_id}.json"
    if not path_file.exists():
        raise FileNotFoundError(f"Path '{path_id}' not found")
    return json.loads(path_file.read_text(encoding="utf-8"))


def _plan_joint_path(request: PathPlanRequest):
    planner_name = request.planner_name or "RRTConnect"
    planner = sim_env.pb_ompl_interface

    sim_env.robot_list[0].set_state(request.start_joints)

    if planner_name in {"RRTConnect_Custom", "RRTConnect"} and hasattr(planner, "get_T_goal") and hasattr(planner, "set_tsRRT_sample"):
        planner.get_T_goal(request.target_joints, tcp_name="rolling_tool")
        planner.z_range = (0.01, 0.2)
        planner.x_range = (-0.01, 0.01)
        planner.y_range = (-0.001, 0.001)
        planner.yaw_range = 30
        planner.roll_range = 5
        planner.pitch_range = 5
        planner.set_tsRRT_sample()
        planner.set_planner("RRTConnect")
        return planner.plan(request.target_joints, allowed_time=request.allowed_time)

    planner.set_planner(planner_name)
    return planner.plan_start_goal(
        request.start_joints,
        request.target_joints,
        allowed_time=request.allowed_time,
    )


def _get_current_pose(reference_frame: str):
    robot = sim_env.robot_list[0]
    if reference_frame == "body":
        return robot.get_pos_ori_from_ik(tcp_name=None)
    if reference_frame == "world":
        return robot.show_link_sys(5, 0.1, 1)
    if reference_frame == "CNC_C":
        return robot.get_position_relative_to_link(
            bodyA_id=robot.id_robot,
            bodyB_id=sim_env.machine.id_robot,
            linkA_id=5,
            linkB_id=sim_env.machine.turntable_index,
        )
    if reference_frame == "work_piece":
        world_pos, world_ori = robot.show_link_sys(5, 0.1, 1)
        result = sim_env.rm_sys.get_point_in_workpiece2world(world_pos, world_ori, inverse=True)
        if result is None:
            raise ValueError("Work piece frame is unavailable")
        return result
    raise ValueError("No reference frame matched")


def _resolve_pose_for_ik(target_position, target_orientation, reference_frame):
    robot = sim_env.robot_list[0]
    orientation = target_orientation
    if orientation is None:
        _, orientation = _get_current_pose(reference_frame)

    if reference_frame == "body":
        return target_position, orientation, "body_sys"
    if reference_frame == "world":
        return target_position, orientation, "world_sys"
    if reference_frame == "CNC_C":
        T_world2robot = sim_env.rm_sys.T_robot2world.copy()
        T_c2world = robot.pos_to_matrix([0, 0, -sim_env.machine.C_in_sys0], [0, 0, 0, 1])
        T_c2target = robot.pos_to_matrix(target_position, orientation)
        T_robot2target = np.linalg.inv(T_world2robot) @ np.linalg.inv(T_c2world) @ T_c2target
        pos, ori = robot.matrix_to_pos(T_robot2target)
        return pos, ori, "body_sys"
    if reference_frame == "work_piece":
        result = sim_env.rm_sys.get_point_in_workpiece2robot(target_position, orientation)
        if result is None:
            raise ValueError("Work piece frame is unavailable")
        pos, ori = result
        return pos, ori, "body_sys"
    raise ValueError("No reference frame matched")


def _compute_joint_state_for_target(request: TargetJointStateRequest):
    robot = sim_env.robot_list[0]
    pos, ori, inverse_mode = _resolve_pose_for_ik(
        request.target_position,
        request.target_orientation,
        request.reference_frame,
    )
    previous_inverse_mode = robot.inverse_mode
    try:
        robot.inverse_mode = inverse_mode
        start_eve = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933,
                     -1.8410220234890533,
                     -0.6757545624540242]
        joints_value = robot.get_state_from_ik(pos, ori,start=start_eve, maxNumIteration=10000, tcp_name="rolling_tool")
    finally:
        robot.inverse_mode = previous_inverse_mode

    return joints_value, pos, ori


from tqdm import tqdm
def _generate_rolling_joint_path(tool_path_file: str):
    cls_path = Path(tool_path_file)
    if not cls_path.exists():
        raise FileNotFoundError(f"Tool path file '{tool_path_file}' not found")
    if not hasattr(sim_env, "rm_sys"):
        raise ValueError("RM system is unavailable")
    if sim_env.rm_sys.T_workpiece2robot is None:
        raise ValueError("Work piece transform is unavailable")

    robot = sim_env.robot_list[0]
    if "rolling_tool" not in robot.tcp_list:
        raise ValueError("Robot TCP 'rolling_tool' is unavailable")


    joints_list = []
    start = list(robot.get_joints_states())
    start = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933, -1.8410220234890533,
             -0.6757545624540242]
    previous_inverse_mode = robot.inverse_mode
    try:
        goto, origin_data = sim_env.rm_sys.read_cls_file(sim_env.robot_list[0], cls_path, inverse=True)
        pos_list, ori_list = [], []
        for item in goto:
            # 解包位置信息pos (X/Y/Z)
            pos_list.append((item['X'], item['Y'], item['Z']))
            # 解包姿态信息ori (x/y/z/w)
            ori_list.append((item['O']['x'], item['O']['y'], item['O']['z'], item['O']['w']))

        pairs = zip(pos_list[:], ori_list[:])
        total_steps = min(len(pos_list[:]), len(ori_list[:]))

        for i, (pos, ori) in enumerate(tqdm(pairs, total=total_steps, desc="Planning path")):
            joints = sim_env.robot_list[0].get_state_from_ik(pos,
                                                             ori,
                                                             start=start, maxNumIteration=10000,
                                                             tcp_name="rolling_tool")
            start = joints

            joints_list.append(joints)

    finally:
        robot.inverse_mode = previous_inverse_mode

    if not joints_list:
        raise ValueError("No valid GOTO entries were found in the tool path file")
    return joints_list



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


@app.post("/reset_joints_state")
async def reset_joints_state(request: JointMoveRequest):
    """ API: 重置机械臂关节状态 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        sim_env.robot_list[0].set_joints_states(request.target_joint_angles)
        return {"status": "success", "message": "Joints state reset"}
    except Exception as e:
        print("[execution:simulation:api:reset_joints_state] Error resetting joints state:", e)
        return {"status": "error", "message": str(e)}


@app.post("/move_robot_to_target")
async def move_robot_to_target(request: PosMoveRequest):
    """ API: 让机械臂运动 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        joint_request = TargetJointStateRequest(
            robot_id=request.robot_id,
            target_position=request.target_position,
            target_orientation=request.target_orientation,
            reference_frame=request.reference_frame,
        )
        joints_value, _, _ = _compute_joint_state_for_target(joint_request)
        sim_env.robot_list[0].joint_move_once(joints_value, maxVelocity=request.maxVelocity)

        return {"status": "success", "message": "Robot moved to target"}

    except Exception as e:
        print("[execution:simulation:api:move_robot_to_target] Error moving robot to target:", e)
        return {"status": "error", "message": str(e)}


@app.post("/get_target_joint_state")
async def get_target_joint_state(request: TargetJointStateRequest):
    """ API: 根据目标位姿获取关节角 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        joints_value, resolved_pos, resolved_ori = _compute_joint_state_for_target(request)
        return {
            "status": "success",
            "message": "Target Joint state computed",
            "joint_state": list(joints_value),
            # "target_pose_in_robot_frame": {   # 返回解析后的目标位姿，方便调试和验证
            #     "pos": list(resolved_pos),
            #     "ori": list(resolved_ori),
            # },
        }
    except Exception as e:
        print("[execution:simulation:api:get_target_joint_state] Error computing joint state:", e)
        return {"status": "error", "message": str(e)}

@app.post("/joint_move")
async def joint_move(request: JointMoveRequest):
    """ API: joint move关节状态 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        sim_env.robot_list[0].joint_move_once(request.target_joint_angles, maxVelocity=request.maxVelocity)
        return {"status": "success", "message": "Joints state reset"}
    except Exception as e:
        print("[execution:simulation:api:reset_joints_state] Error resetting joints state:", e)
        return {"status": "error", "message": str(e)}




@app.post("/plan_path")
async def plan_path(request: PathPlanRequest):
    """
     API: 规划路径
    """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        running_flag = False
        if sim_env.is_running:
            running_flag = True
            sim_env.stop_simulation()

        if request.start_joints is None:
            start_joints = sim_env.robot_list[0].get_joints_states()
            request.start_joints = start_joints


        try:
            res, path = _plan_joint_path(request)
        finally:
            if running_flag:
                sim_env.start_simulation()

        if not res:
            return {"status": "failed", "message": "No collision-free path found", "path": None}

        path_id, path_file = _save_planned_path(
            planner_name=request.planner_name or "RRTConnect",
            start_joints=request.start_joints,
            target_joints=request.target_joints,
            path=path,
        )
        return {
            "status": "success",
            "message": "Path planned successfully",
            "path_id": path_id,
            # "path": path, # 不直接返回路径数据，避免过大负载。客户端可以通过 path_id 再请求一次来获取路径详情。
            "waypoint_count": len(path),
            "storage": str(path_file),
        }
    except Exception as e:
        print("[execution:simulation:api:plan_path] Error planning path:", e)
        return {"status": "error", "message": str(e)}



@app.post("/get_rolling_path")
async def get_rolling_path(request: RollingPathRequest):
    """ API: 根据刀位文件生成滚压路径 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        if "区域1" in request.tool_path_name:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域1.cls"
        elif "区域2" in request.tool_path_name:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域2.cls"
        elif "区域3" in request.tool_path_name:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域3.cls"
        elif "区域4" in request.tool_path_name:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域4.cls"
        elif "区域0" in request.tool_path_name:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域0.cls"
        else:
            tool_path_file = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/runtime/UG/6061_A_区域1.cls"


        joints_list = _generate_rolling_joint_path(tool_path_file)
        start_joints = joints_list[0]
        path_id, path_file = _save_planned_path(
            planner_name="rolling_path",
            start_joints=start_joints,
            target_joints=joints_list[-1],
            path=joints_list,
        )
        return {
            "status": "success",
            "message": "Rolling path generated",
            "path_id": path_id,
            "start_joints": start_joints,
            "waypoint_count": len(joints_list),
            "storage": str(path_file),
        }
    except Exception as e:
        print("[execution:simulation:api:get_rolling_path] Error generating rolling path:", e)
        return {"status": "error", "message": str(e)}


@app.post("/execute_path")
async def execute_path(request: ExecutePathRequest):
    """ API: 执行路径 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}

        joints_list = request.joints_list
        path_id = request.path_id
        if joints_list is None:
            if not path_id:
                return {"status": "error", "message": "Either joints_list or path_id is required"}
            payload = _load_planned_path(path_id)
            joints_list = payload.get("path")

        if not joints_list:
            return {"status": "error", "message": "Path is empty"}

        if request.collision_detection:
            path_safe = True
            for i,joints in enumerate(joints_list):
                sim_env.step_simulation()
                sim_env.robot_list[0].set_joints_states(joints)
                safe = sim_env.pb_ompl_interface.is_state_valid(joints)
                if not safe:
                    path_safe = False
                    print(f"Collision detected at step {i} for joints: {joints}")
                    # time.sleep(1)
            if path_safe:
                return {
                    "status": "success",
                    "message": "Path executed with collision detection, no collision detected",
                    "path_id": path_id,
                    "waypoint_count": len(joints_list),
                }
            else:
                return {
                    "status": "failed",
                    "message": "Collision detected during path execution",
                    "path_id": path_id,
                    "waypoint_count": len(joints_list),
                }

        else:
            if sim_env.pb_ompl_interface:
                sim_env.pb_ompl_interface.execute(joints_list, dynamics=request.dynamics)
            return {
                "status": "success",
                "message": "Path executed",
                "path_id": path_id,
                "waypoint_count": len(joints_list),
            }
    except Exception as e:
        print("[execution:simulation:api:execute_path] Error executing path:", e)
        return {"status": "error", "message": str(e)}




@app.post("/update_env_by_calibration")
async def update_env_by_calibration(request: ExecutePathRequest):
    """ API: 执行路径 """
    try:
        if len(sim_env.robot_list) == 0:
            return {"status": "error", "message": "No robot loaded"}
        if sim_env.pb_ompl_interface:
            sim_env.pb_ompl_interface.execute(request.joints_list, dynamics=request.dynamics)
        return {"status": "success", "message": "Path executed"}
    except Exception as e:
        print("[execution:simulation:api:execute_path] Error executing path:", e)
        return {"status": "error", "message": str(e)}


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
        pos, ori = _get_current_pose(request.reference_frame)

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




@app.post("/get_machine_axis_values")
async def get_machine_axis_values():
    """API: 获取机床 ACXYZ 轴当前值。"""
    try:
        if not hasattr(sim_env, "machine") or sim_env.machine is None:
            return {"status": "error", "message": "No machine loaded"}
        axis_values = sim_env.machine.get_joints_states()
        return {
            "status": "success",
            "axis_labels": ["A", "C", "X", "Y", "Z"],
            "axis_values": list(axis_values),
        }
    except Exception as e:
        print("[execution:simulation:api:get_machine_axis_values] Error getting machine axis values:", e)
        return {"status": "error", "message": str(e)}


@app.post("/set_machine_axis_values")
async def set_machine_axis_values(request: MachineAxisRequest):
    """API: 设置机床 ACXYZ 轴目标值。"""
    try:
        if not hasattr(sim_env, "machine") or sim_env.machine is None:
            return {"status": "error", "message": "No machine loaded"}
        if len(request.target_axis_values) != 5:
            return {"status": "error", "message": "Machine axis values must contain exactly 5 numbers (A, C, X, Y, Z)"}
        # sim_env.machine.joint_move_once(request.target_axis_values, maxVelocity=request.maxVelocity)
        sim_env.machine.set_joints_states(request.target_axis_values)
        return {
            "status": "success",
            "message": "Machine axis values updated",
            "axis_labels": ["A", "C", "X", "Y", "Z"],
            "axis_values": list(request.target_axis_values),
        }
    except Exception as e:
        print("[execution:simulation:api:set_machine_axis_values] Error setting machine axis values:", e)
        return {"status": "error", "message": str(e)}


@app.post("/reset_machine_axis_values")
async def reset_machine_axis_values(request: MachineAxisRequest):
    """API: 直接重置机床 ACXYZ 轴当前值。"""
    try:
        if not hasattr(sim_env, "machine") or sim_env.machine is None:
            return {"status": "error", "message": "No machine loaded"}
        if len(request.target_axis_values) != 5:
            return {"status": "error", "message": "Machine axis values must contain exactly 5 numbers (A, C, X, Y, Z)"}
        sim_env.machine.set_joints_states(request.target_axis_values)
        return {
            "status": "success",
            "message": "Machine axis values reset",
            "axis_labels": ["A", "C", "X", "Y", "Z"],
            "axis_values": list(request.target_axis_values),
        }
    except Exception as e:
        print("[execution:simulation:api:reset_machine_axis_values] Error resetting machine axis values:", e)
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
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            # 说明这个 websocket 已经不在列表里了（可能之前断开时就删过）
            print("[RobotStateManager] disconnect: websocket not in active_connections, ignore.")

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
            # await websocket.receive_text()
            await asyncio.sleep(3600)   # 不期待客户端发消息的话，这样挂着就行.避免心跳得不到响应
    except WebSocketDisconnect:
        robot_state_manager.disconnect(websocket)
        print("Client disconnected")
        print(f"Exception in websocket_endpoint:", WebSocketDisconnect)


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



class MachineStateManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            print("[MachineStateManager] disconnect: websocket not in active_connections, ignore.")

    async def send_machine_state(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except WebSocketDisconnect:
                self.active_connections.remove(connection)


machine_state_manager = MachineStateManager()


@app.websocket("/ws/machinestate")
async def machine_websocket_endpoint(websocket: WebSocket):
    """WebSocket 路由，用于订阅机床状态信息。"""
    await machine_state_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(3600)
    except WebSocketDisconnect:
        machine_state_manager.disconnect(websocket)
        print("Machine state client disconnected")


current_machine_task = None


@app.post("/publish_machine_state")
async def publish_machine_state(request: dict):
    """用于发布机床状态信息，推送到所有连接的客户端。"""
    try:
        global current_machine_task
        on_pub = request.get("on_subscribe", True)

        async def pub_machine_state():
            while True:
                try:
                    await asyncio.sleep(0.1)
                    if not hasattr(sim_env, "machine") or sim_env.machine is None:
                        continue
                    axis_values = sim_env.machine.get_joints_states()
                    machine_state = {
                        "status": "success",
                        "axis_labels": ["A", "C", "X", "Y", "Z"],
                        "axis_values": list(axis_values),
                    }
                    await machine_state_manager.send_machine_state(machine_state)
                except asyncio.CancelledError:
                    print("Publishing machine state task was cancelled.")
                    break

        if on_pub:
            if current_machine_task and not current_machine_task.done():
                current_machine_task.cancel()
                print("Previous machine state task cancelled.")

            current_machine_task = asyncio.create_task(pub_machine_state())
            return {"status": "success", "message": "Machine state publishing started"}

        if current_machine_task and not current_machine_task.done():
            current_machine_task.cancel()
            await current_machine_task
            return {"status": "success", "message": "Machine state publishing canceled"}

        return {"status": "error", "message": "No active machine state task to cancel"}

    except Exception as e:
        print("[execution:simulation:api:publish_machine_state] Error publishing machine state:", e)
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
                ws_ping_interval=None,  # 关闭 WS 心跳
                ws_ping_timeout=None,  # 或者给个很大的秒数，如 600
                )  # 设置为8001端口运行

if __name__ == "__main__":
    run_pybullet_service()
