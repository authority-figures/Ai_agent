from pydantic import BaseModel, Field
from typing import List, Optional
import json


class PlanStep(BaseModel):
    id: str
    action: str
    param: dict = Field(default_factory=dict)
    depends: List[str] = Field(default_factory=list)

class Progress(BaseModel):
    current_step: int = 0
    percent: int = 0
    step_status: dict = Field(default_factory=dict)   # {"s1":"ok","s2":"running"}
    log: List[str] = Field(default_factory=list)

class Result(BaseModel):
    data: Optional[dict] = None
    error: str = ""

class Task(BaseModel):
    task_id: str
    task_name: str
    status: str = "pending"          # pending | planning | running | paused | success | failed | cancelled
    created_at: int
    updated_at: int
    owner: str = ""
    description: str = ""
    plan: Optional[List[PlanStep]] = None
    progress: Optional[Progress] = None
    result: Optional[Result] = None
    ttl: int = 86400

    # def to_hdict(self) -> dict:
    #     """转成扁平 Hash 存 Redis"""
    #     return {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    #             for k, v in self.dict().items()}
    #
    # @staticmethod
    # def from_hdict(data: dict) -> "Task":
    #     """从 Redis Hash 反序列化"""
    #     return Task(**{k: json.loads(v) if k in {"plan","progress","result"} else v
    #                    for k, v in data.items()})

    def to_hdict(self) -> dict:
        """转成扁平 Hash 存 Redis，处理 None 值"""
        data = self.dict()
        for k, v in data.items():
            if v is None:
                # 将 None 转换为 "null"（或空字符串，根据业务需求）
                data[k] = "null"
            elif isinstance(v, (dict, list)):
                # 序列化字典/列表
                data[k] = json.dumps(v, ensure_ascii=False)
            # 其他类型（str/int 等）直接保留
        return data

    @staticmethod
    def from_hdict(data: dict) -> "Task":
        """从 Redis Hash 反序列化，恢复 None 值"""
        for k, v in data.items():
            if v == "null":
                # 将 "null" 转回 None
                data[k] = None
            elif k in {"plan", "progress", "result"}:
                # 反序列化字典/列表
                data[k] = json.loads(v)
        return Task(**data)



# 定义响应模型（包含 status 和 data 字段）
class TaskResponse(BaseModel):
    status: str
    message: Optional[Task]  # data 可为 Task 实例或 None

