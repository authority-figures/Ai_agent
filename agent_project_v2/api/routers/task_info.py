from fastapi import APIRouter, Depends, HTTPException
from typing import List
# from db.task_repo import TaskRepo, get_repo   # 单例依赖
from agent.services.task_repo import *
from core.task import PlanStep
from core.service_locator import ServiceLocator

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# ---------- 依赖注入 ----------
# def repo_dep() -> TaskRepo:
#     return get_repo()          # 单例

def get_task_repo() -> TaskRepo:
    repo = ServiceLocator.get('task_repo')
    if repo is None:
        raise HTTPException(status_code=500, detail="TaskRepo not available")
    return repo

@router.post("/create", response_model=dict)
async def create_task(
    owner: str,
    desc: str,
    task_name: str,
    repo: TaskRepo = Depends(get_task_repo)
) -> dict:
    try:
        print("into create task api")
        return await repo.create(task_name, owner, desc)
    except Exception as e:
        raise HTTPException(500, f"failed to create task: {e}")

@router.get("/{task_id}")
async def get_task(task_id: str, repo: TaskRepo = Depends(get_task_repo)) -> TaskResponse:
    t = await repo.get(task_id)
    if not t:
        raise HTTPException(404, "[task_info:get_task] task not found")
    return t

@router.put("/{task_id}/plan")
async def push_plan(
    task_id: str,
    plan: List[PlanStep],
    repo: TaskRepo = Depends(get_task_repo)
) -> bool:
    ok = await repo.push_plan(task_id, plan)
    if not ok:
        raise HTTPException(409, "plan already pushed or task not in pending")
    return ok

@router.patch("/{task_id}/progress")
async def update_progress(
    task_id: str,
    percent: int,
    log: str,
    repo: TaskRepo = Depends(get_task_repo)
) -> bool:
    ok = await repo.update_progress(task_id, percent, log)
    if not ok:
        raise HTTPException(404, "task progress not found")
    return ok
