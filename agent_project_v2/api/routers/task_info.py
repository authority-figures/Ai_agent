from fastapi import APIRouter, Depends, HTTPException
from typing import List
# from db.task_repo import TaskRepo, get_repo   # 单例依赖
from agent.services.task_repo import *
from core.task import PlanStep
from core.service_locator import ServiceLocator
from fastapi import Body

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
    plan: List[PlanStep] = Body(...), # 明确来自 body
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


@router.get("/", response_model=List[dict])
async def get_all_tasks(repo: TaskRepo = Depends(get_task_repo)):
    """返回所有任务的列表"""
    try:
        # 假设 redis 里任务 key 格式为 task:task_id
        keys = await repo.redis.keys("task:*")
        tasks = []
        for key in keys:
            data = await repo.redis.hgetall(key)
            if data:
                tasks.append(Task.from_hdict(data).dict())
        return tasks
    except Exception as e:
        raise HTTPException(500, f"Failed to get all tasks: {e}")



@router.delete("/{task_id}")
async def delete_task(task_id: str, repo: TaskRepo = Depends(get_task_repo)) -> dict:
    """删除指定 task_id 的任务"""
    try:
        key = f"task:{task_id}"
        deleted = await repo.redis.delete(key)
        if deleted == 0:
            raise HTTPException(404, detail=f"Task {task_id} not found")
        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to delete task {task_id}: {e}")


@router.delete("/")
async def delete_all_tasks(repo: TaskRepo = Depends(get_task_repo)) -> dict:
    """删除所有任务（慎用）"""
    try:
        keys = await repo.redis.keys("task:*")
        if not keys:
            return {"message": "No tasks found"}
        deleted = await repo.redis.delete(*keys)
        return {"message": f"Deleted {deleted} tasks successfully"}
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to delete all tasks: {e}" )

