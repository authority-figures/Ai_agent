from pydantic import BaseModel
from typing import Optional


class GetPosOriRequest(BaseModel):
    object_id: Optional[int]  # 使用 Optional 表示可以为 None
    reference_frame: str = "world"  # 默认参考系为 "world" "world"|"body|CNC_C"

    def to_dict(self):
        """将对象转换为字典，便于 JSON 序列化"""
        return self.dict()  # Pydantic 的 `dict()` 方法将模型转化为字典