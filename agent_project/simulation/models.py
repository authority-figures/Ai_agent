# 专门存放数据模型


from pydantic import BaseModel
from typing import List,Optional

class LoadObjectRequest(BaseModel):
    urdf_path: str
    basePosition: list[float]
    baseOrientation: list[float] = [0, 0, 0, 1]
    useFixedBase: bool = True

class GetIDRequest(BaseModel):
    robot_id: int


class TargetMoveRequest(BaseModel):
    robot_id: int
    target_position: List[float]  # 确保关节角是浮点数列表
    target_orientation: Optional[List[float]] = None  # 确保关节角是浮点数列表
    maxVelocity: float = 10

class MoveRequest(BaseModel):
    joint_positions: List[float]  # 确保关节角是浮点数列表


class PosAndOri(BaseModel):
    pos: List[float]
    ori: List[float]

class CreateCubeRequest(PosAndOri):
    half_extents: List[float] = [0.1,0.1,0.1]
    mass: float = 1.0
    color: List[float] = [1, 0, 0, 1]

