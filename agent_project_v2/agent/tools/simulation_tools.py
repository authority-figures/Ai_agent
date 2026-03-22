from langchain.tools import tool  # ✅ 直接使用装饰器
import httpx
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.simulation_request import (
    ExecutePathRequest,
    GetPosOriRequest,
    PathPlanRequest,
    PosMoveRequest,
    TargetJointStateRequest,
    RollingPathRequest,
)

SIMULATION_API_BASE_URL = "http://localhost:8001"


@tool
async def get_robot_end_pos_and_ori(description, robot_id, reference_frame="world"):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - reference_frame (str): 参考系，默认 "world" "world"|"body"|"CNC_C"|"work_piece"

    返回:
    - dict: API 响应数据，包含 "status"、"messages":`end_pos` 和 `end_ori`
    """
    url = f"{SIMULATION_API_BASE_URL}/get_robot_end_pos_and_ori"
    try:
        request = GetPosOriRequest(object_id=robot_id, reference_frame=reference_frame)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict())
            if response.status_code == 200:
                return response.json()
            print(f"[simulation_tools:get_robot_end_pos_and_ori] HTTP Error: {response.status_code}, {response.text}")
            return {"status": "error", "message": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}



class GetTargetJointStateToolInput(BaseModel):
    description: str = Field(..., description="对任务的详细复述，需包含输入参数。")
    robot_id: int = Field(..., description="机械臂的 ID。")
    target_position: List[float] = Field(..., description="目标位置 [x, y, z]。")
    target_orientation: Optional[List[float]] = Field(
        default=None,
        description="目标姿态四元数 [qx, qy, qz, qw]；若为 None，则使用当前姿态。",
    )
    reference_frame: Literal["world", "body", "CNC_C", "work_piece"] = Field(
        ...,
        description='参考系，必须显式填写，支持 "world"|"body"|"CNC_C"|"work_piece"。',
    )
@tool(args_schema=GetTargetJointStateToolInput)
async def get_target_joint_state(
    description,
    robot_id,
    target_position,
    target_orientation,
    reference_frame,
):
    """
    获取目标姿态下的机械臂关节状态，支持指定参考系（世界坐标系、机械臂坐标系、工件坐标系等）。如果未提供目标姿态，则默认使用当前姿态进行计算。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - target_position (list[float]): 目标位置
    - target_orientation (list[float] | None): 目标姿态；为 None 时使用当前姿态
    - reference_frame (str): 参考系，支持 "world":世界坐标系|"body":机械臂坐标系|"CNC_C"|"work_piece":工件坐标系

    返回:
    - dict: 包含 `status`、`joint_state` 和归一化后的目标位姿
    """
    url = f"{SIMULATION_API_BASE_URL}/get_target_joint_state"
    try:
        request = TargetJointStateRequest(
            robot_id=robot_id,
            target_position=target_position,
            target_orientation=target_orientation,
            reference_frame=reference_frame,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=30)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": f"Failed to get target joint state: {response.text}"}
    except Exception as e:
        print(f"[simulation_tools:get_target_joint_state] Exception: {e}")
        return {"status": "error", "message": str(e)}


class PlanCollisionFreePathToolInput(BaseModel):
    description: str = Field(
        ...,
        description="对任务的详细复述，需包含输入参数。"
    )
    robot_id: int = Field(
        ...,
        description="机械臂的 ID。"
    )

    target_joints: List[float] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="目标关节角，必须填写，且必须为长度为 6 的列表。"
    )

    start_joints: Optional[List[float]] = Field(
        default=None,
        min_length=6,
        max_length=6,
        description=(
            "起始关节角，共 6 个关节值"
            "若为 None 或不提供，则默认使用当前机械臂关节状态作为起点。"
            "若在规划时发现只提供了一个关节状态，则该状态为target_joints，start_joints为None，"
        ),
    )
    planner_name: str = Field(
        default="RRTConnect",
        description='规划器名称，默认 "RRTConnect"。'
    )
    allowed_time: float = Field(
        default=20.0,
        description="规划允许的最大耗时，单位秒，默认 20.0。"
    )

@tool(args_schema=PlanCollisionFreePathToolInput)
async def plan_collision_free_path(
    description,
    robot_id,
    target_joints,
    start_joints = None,
    planner_name="RRTConnect",
    allowed_time=20.0,
):
    """
    规划一条机械臂从起始关节到目标关节的无碰撞路径，并将结果保存在仿真服务中。
    该工具一般用于插入路径规划

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID（当前仿真环境仅使用已加载的首个机器人）
    - target_joints (list[float]): 目标关节角  （必须提供，且长度必须为 6）
    - start_joints (list[float]|None): 起始关节角 （如果为 None 或空列表，则默认使用当前关节状态）
    - planner_name (str): 规划器名称，默认 RRTConnect
    - allowed_time (float): 规划超时时间，默认 20 秒

    返回:
    - dict: 包含 `status`、`path_id`、`path`、`waypoint_count` 等字段
    """
    url = f"{SIMULATION_API_BASE_URL}/plan_path"
    try:
        request = PathPlanRequest(
            planner_name=planner_name,
            start_joints=start_joints,
            target_joints=target_joints,
            allowed_time=allowed_time,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=200)
            if response.status_code == 200:
                data = response.json()
                data.setdefault("robot_id", robot_id)
                return data
            return {"status": "error", "message": f"Failed to plan path: {response.text}"}
    except Exception as e:
        print(f"[simulation_tools:plan_collision_free_path] Exception: {e}")
        return {"status": "error", "message": str(e)}


class GetRollingPathToolInput(BaseModel):
    description: str = Field(..., description="对任务的详细复述，需包含输入参数。")
    robot_id: int = Field(..., description="机械臂的 ID。")
    tool_path_name: str = Field(..., description="刀位文件名称")


@tool(args_schema=GetRollingPathToolInput)
async def get_rolling_path(
    description: str,
    robot_id: int,
    tool_path_name: str,
):
    """
    获取滚压路径的关节角列表，并返回对应 path_id 和起始关节角。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - tool_path_name (str): 刀位文件名称 "区域1" | "区域2" | "区域3" | "区域4"

    返回:
    - dict: 包含 `status`、`path_id`、`start_joints` 和 `waypoint_count`
    """
    url = f"{SIMULATION_API_BASE_URL}/get_rolling_path"
    try:
        request = RollingPathRequest(
            robot_id=robot_id,
            tool_path_name=tool_path_name,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=200)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": f"Failed to get rolling path: {response.text}"}
    except Exception as e:
        print(f"[simulation_tools:get_rolling_path] Exception: {e}")
        return {"status": "error", "message": str(e)}

@tool
async def execute_planned_path(
    description,
    robot_id,
    path_id=None,
    joints_list=None,
    dynamics=False,
    collision_detection=True,
):
    """
    执行已规划好的路径。优先使用 path_id 从仿真服务中加载路径，也支持直接传入 joints_list。

    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID（当前仿真环境仅使用已加载的首个机器人）
    - path_id (str, optional): 规划阶段返回的路径标识符
    - joints_list (list[list[float]], optional): 直接执行的关节路径
    - dynamics (bool): 是否使用动力学执行，默认 False
    - collision_detection (bool): 是否启用碰撞检测，默认 True

    返回:
    - dict: 包含 `status` 和 `message`
    """
    url = f"{SIMULATION_API_BASE_URL}/execute_path"
    try:
        request = ExecutePathRequest(
            joints_list=joints_list,
            path_id=path_id,
            dynamics=dynamics,
            collision_detection = collision_detection,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=200)
            if response.status_code == 200:
                data = response.json()
                data.setdefault("robot_id", robot_id)
                return data
            return {"status": "error", "message": f"Failed to execute path: {response.text}"}
    except Exception as e:
        print(f"[simulation_tools:execute_planned_path] Exception: {e}")
        return {"status": "error", "message": str(e)}


@tool
async def set_robot_end_pos_and_ori(description, robot_id, pos, ori, reference_frame, maxVelocity=1):
    """
    设置机械臂末端位置和姿态。
    参数:
    - description (str): 对任务的详细复述,包含输入的参数
    - robot_id (int): 机械臂的 ID
    - pos (list): 目标位置 [x, y, z]
    - ori (list): 目标姿态 [qx, qy, qz, qw]
    - reference_frame (str): 参考系，默认 "world" "world"|"body"|"CNC_C"|"work_piece"，分别表示世界坐标系，机械臂基座坐标系，CNC_C轴转台坐标系和工件坐标系
    - maxVelocity (float): 最大速度，默认 1
    """

    url = f"{SIMULATION_API_BASE_URL}/move_robot_to_target"
    try:
        request = PosMoveRequest(
            robot_id=robot_id,
            target_position=pos,
            target_orientation=ori,
            reference_frame=reference_frame,
            maxVelocity=maxVelocity,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request.to_dict(), timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to set_robot_end_pos_and_ori"}
    except Exception as e:
        print(f"[CustomSimulationEnv:set_robot_tcp_pos_and_ori] Exception: {e}")
        return {"status": "error", "message": str(e)}


using_tools = [
    # get_robot_end_pos_and_ori,
    get_target_joint_state,
    set_robot_end_pos_and_ori,
    plan_collision_free_path,
    execute_planned_path,
    get_rolling_path,
]