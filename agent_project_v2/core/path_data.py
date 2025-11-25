# core/path_data.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class PathData(BaseModel):
    name: str                             # path_name
    joints_list: List[List[float]]        # n x 6 关节路径
    description: str = ""
    planner: Optional[str] = None         # 比如 RRTConnect
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    meta: Dict[str, Any] = {}             # 其他附加信息，比如起点/终点工位等

    def to_redis_hash(self) -> dict:
        """序列化为 Redis Hash 可用的 dict（字符串为主）"""
        import json
        return {
            "type": "path",
            "name": self.name,
            "description": self.description,
            "planner": self.planner or "",
            "created_at": str(self.created_at),
            "meta": json.dumps(self.meta, ensure_ascii=False),
            "joints_list": json.dumps(self.joints_list, ensure_ascii=False),
        }

    @classmethod
    def from_redis_hash(cls, h: dict) -> "PathData":
        import json
        if not h:
            raise ValueError("empty hash")
        return cls(
            name=h.get("name", ""),
            description=h.get("description", ""),
            planner=h.get("planner") or None,
            created_at=int(h.get("created_at", "0")),
            meta=json.loads(h.get("meta", "{}")),
            joints_list=json.loads(h.get("joints_list", "[]")),
        )


class PathMeta(BaseModel):
    """不含 joints_list 的轻量信息，用于列表展示 / Agent 选择"""
    name: str
    description: str = ""
    planner: Optional[str] = None
    created_at: int
    length: int = 0                # joints_list 的长度（点数）
