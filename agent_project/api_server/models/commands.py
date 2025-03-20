from pydantic import BaseModel
from typing import List,Optional



class PosAndOri(BaseModel):
    pos: List[float]
    ori: List[float]


class MoveCommand(BaseModel):
    target: List[float]  # 目标位置 (x, y, z)

class Load_ObjectCommand(BaseModel):
    urdf_path: str
    basePosition: list[float]
    baseOrientation: list[float] = [0,0,0,1]


class GetIDRequest(BaseModel):
    robot_id: int

class TargetMoveRequest(BaseModel):
    robot_id: int
    target_position: List[float]
    target_orientation: Optional[List[float]] = None
    maxVelocity: float = 10


class CreateCubeRequest(PosAndOri):

    half_extents: List[float] = [0.1,0.1,0.1]
    mass: float = 1.0
    color: List[float] = [1, 0, 0, 1]
