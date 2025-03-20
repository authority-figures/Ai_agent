
from pydantic import BaseModel


class MoveParams(BaseModel):
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float

class JointValue(BaseModel):
    joint_position: list[float]

# 笛卡尔坐标系下的位置和姿态
class CartesianPose(BaseModel):
    position: list[float]
    orientation: list[float]

class JointMoveParams(JointValue):
    move_mode: int = 0
    speed: int = 10
    acc: int = 10
    is_block: bool = True
    tol: float = 0.1