from pydantic import BaseModel
from typing import Optional,List



class JointMoveRequest(BaseModel):
    joint_positions: List[float]
    move_mode: int = 0  # 0表示绝对位置，1表示相对位置
    speed: Optional[float] = 1
    acc: Optional[float] = 1
    is_block: bool = False
    tol: Optional[float] = 0.0

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典