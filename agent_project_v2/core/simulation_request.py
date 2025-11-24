from pydantic import BaseModel
from typing import Optional,List


class GetPosOriRequest(BaseModel):
    object_id: Optional[int]  # 使用 Optional 表示可以为 None
    reference_frame: str = "world"  # 默认参考系为 "world" "world"|"body|CNC_C"

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典

class PosMoveRequest(BaseModel):
    robot_id: Optional[int]
    target_position: List[float]  # 确保关节角是浮点数列表
    target_orientation: Optional[List[float]] = None  # 确保关节角是浮点数列表
    reference_frame: str = "world"  # 默认参考系为 "world" "world"|"body|CNC_C"
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
    start_joints: List[float]  # 确保关节角是浮点数列表
    target_joints: List[float]  # 确保关节角是浮点数列表


    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典

class ExecutePathRequest(BaseModel):
    joints_list: List[List[float]]  # 确保关节角是浮点数列表的列表
    maxVelocity: float = 1
    dynamics: bool = False

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典