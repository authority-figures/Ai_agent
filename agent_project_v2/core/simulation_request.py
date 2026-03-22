from pydantic import BaseModel
from typing import Optional, List


class GetPosOriRequest(BaseModel):
    object_id: Optional[int]  # 使用 Optional 表示可以为 None
    reference_frame: str = "world"  # 默认参考系为 "world" "world"|"body"|"CNC_C"|"work_piece"

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典


class PosMoveRequest(BaseModel):
    robot_id: Optional[int]
    target_position: List[float]  # 确保关节角是浮点数列表
    target_orientation: Optional[List[float]] = None  # 确保关节角是浮点数列表
    reference_frame: str = "world"  # 默认参考系为 "world" "world"|"body"|"CNC_C"|"work_piece"
    maxVelocity: float = 10

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典


class JointMoveRequest(BaseModel):
    robot_id: Optional[int] = None
    target_joint_angles: List[float]  # 确保关节角是浮点数列表
    maxVelocity: float = 1

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典


class PathPlanRequest(BaseModel):
    planner_name: Optional[str] = "RRTConnect_Custom"
    start_joints: Optional[List[float]] = None # 确保关节角是浮点数列表
    target_joints: List[float]  # 确保关节角是浮点数列表
    allowed_time: float = 20.0

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典


class TargetJointStateRequest(BaseModel):
    robot_id: Optional[int] = None
    target_position: List[float]
    target_orientation: Optional[List[float]] = None
    reference_frame: str = "world"  # "world"|"body"|"CNC_C"|"work_piece"

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()


class RollingPathRequest(BaseModel):
    robot_id: Optional[int] = None
    tool_path_name: str = "区域1"

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()


class ExecutePathRequest(BaseModel):
    joints_list: Optional[List[List[float]]] = None  # 可直接传入路径点
    path_id: Optional[str] = None  # 也可以通过 path_id 引用已保存路径
    maxVelocity: float = 1
    dynamics: bool = False
    collision_detection: bool = True

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典


class MachineAxisRequest(BaseModel):
    target_axis_values: List[float]  # A, C, X, Y, Z
    maxVelocity: float = 1

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()