# api/routers/data_paths.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from agent.services.data_repo import DataRepo
from core.path_data import PathData, PathMeta
from core.service_locator import ServiceLocator   # 跟你 Task 那套保持一致

router = APIRouter(prefix="/api/data", tags=["Data"])


def get_data_repo() -> DataRepo:
    repo = ServiceLocator.get("data_repo")
    if repo is None:
        raise HTTPException(500, "DataRepo not available")
    return repo


@router.post("/paths", response_model=dict)
async def create_or_update_path(path: PathData, repo: DataRepo = Depends(get_data_repo)):
    """新建或更新一条路径"""
    await repo.save_path(path)
    return {"status": "success", "name": path.name}


@router.get("/paths", response_model=List[PathMeta])
async def list_paths(repo: DataRepo = Depends(get_data_repo)):
    """列出所有路径的元信息"""
    return await repo.list_paths()


@router.get("/paths/{name}", response_model=PathData)
async def get_path(name: str, repo: DataRepo = Depends(get_data_repo)):
    """获取完整路径数据"""
    p = await repo.get_path(name)
    if not p:
        raise HTTPException(404, f"path '{name}' not found")
    return p


@router.delete("/paths/{name}", response_model=dict)
async def delete_path(name: str, repo: DataRepo = Depends(get_data_repo)):
    ok = await repo.delete_path(name)
    if not ok:
        raise HTTPException(404, f"path '{name}' not found")
    return {"status": "success", "name": name}
