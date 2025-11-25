# agent/services/data_repo.py
import aioredis
import json
import time
from typing import List, Optional
from fastapi import HTTPException

from core.path_data import PathData, PathMeta


class DataRepo:
    """管理共享数据（path / force / ...），目前先实现 path 部分"""

    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    # ---------------- Path 部分的工具函数 ----------------

    @staticmethod
    def _path_key(name: str) -> str:
        return f"data:path:{name}"

    @staticmethod
    def _path_index_key() -> str:
        return "data:index:paths"

    # ---------------- Path CRUD ----------------

    async def save_path(self, path: PathData) -> None:
        """保存或更新一条路径数据"""
        try:
            key = self._path_key(path.name)
            h = path.to_redis_hash()
            # 额外再存一个 length 字段，方便列表展示
            h["length"] = str(len(path.joints_list))

            async with self.redis.pipeline() as pipe:
                await pipe.hset(key, mapping=h)
                await pipe.sadd(self._path_index_key(), path.name)
                await pipe.execute()

            print(f"[DataRepo] saved path '{path.name}'")
        except Exception as e:
            print(f"[DataRepo] save_path failed: {e}")
            raise HTTPException(500, detail=f"[data_repo] Failed to save path: {e}")

    async def get_path(self, name: str) -> Optional[PathData]:
        """获取完整的路径数据（含 joints_list）"""
        key = self._path_key(name)
        h = await self.redis.hgetall(key)
        if not h:
            return None
        return PathData.from_redis_hash(h)

    async def get_path_joints(self, name: str) -> Optional[List[List[float]]]:
        """只拿 joints_list，供执行工具使用"""
        key = self._path_key(name)
        data = await self.redis.hget(key, "joints_list")
        if not data:
            return None
        return json.loads(data)

    async def list_paths(self) -> List[PathMeta]:
        """列出所有路径的元信息（不含 joints_list）"""
        names = await self.redis.smembers(self._path_index_key())
        result: List[PathMeta] = []
        for n in names:
            key = self._path_key(n)
            h = await self.redis.hgetall(key)
            if not h:
                continue
            try:
                length = int(h.get("length", "0"))
            except ValueError:
                length = 0
            meta = PathMeta(
                name=h.get("name", n),
                description=h.get("description", ""),
                planner=h.get("planner") or None,
                created_at=int(h.get("created_at", "0")),
                length=length,
            )
            result.append(meta)
        # 可以按创建时间排序一下
        result.sort(key=lambda m: m.created_at)
        return result

    async def delete_path(self, name: str) -> bool:
        """删除一条路径"""
        key = self._path_key(name)
        async with self.redis.pipeline() as pipe:
            await pipe.delete(key)
            await pipe.srem(self._path_index_key(), name)
            res = await pipe.execute()
        # res[0] 是 delete 的数量
        return bool(res[0])


# 工厂函数（类似你 TaskRepo 那一套）
def create_data_repo(redis_url: str = "redis://localhost") -> DataRepo:
    return DataRepo(redis_url)

async def create_data_repo_async(redis_url: str = "redis://localhost") -> DataRepo:
    repo = DataRepo(redis_url)
    await repo.redis.ping()
    return repo
