import aioredis, json, time, uuid
from datetime import datetime
from core.task import *
from typing import List, Optional
from fastapi import HTTPException

class TaskRepo:
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def create(self,task_name, owner: str, desc: str, ttl: int = 86400) -> dict:
        try:
            task_id = f"t-{datetime.now():%y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
            task = Task(task_id=task_id, task_name=task_name, status="pending",
                        created_at=int(time.time()),
                        updated_at=int(time.time()),
                        owner=owner, description=desc, ttl=ttl)
            async with self.redis.pipeline() as pipe:
                await pipe.hset(f"task:{task_id}", mapping=task.to_hdict())
                await pipe.expire(f"task:{task_id}", ttl)
                await pipe.execute()

            # 注意：publish 不能放在 pipeline 里（管道适合批量写操作，publish 是即时通知）
            # 发布任务创建消息，通知plan agent（如任务调度器）
            await self.redis.publish("task_channel", task_id)

            print(f"[TaskRepo] created task {task_id}")
            return {"status":"success","data":{"task_id":task_id,"task_name":task_name}}
        except Exception as e:
            print(f"[TaskRepo] create task failed: {e}")
            raise HTTPException(status_code=500, detail=f"[task_repo] Failed to create task: {str(e)}")

    async def get(self, task_id: str) -> TaskResponse:
        try:
            data = await self.redis.hgetall(f"task:{task_id}")
            dict_data = Task.from_hdict(data) if data else None
            if dict_data:
                return TaskResponse(status="success", message=dict_data)
            else:
                return TaskResponse(status="error", message=None)
        except Exception as e:
            print(f"[TaskRepo] get task failed: {e}")
            raise HTTPException(status_code=500, detail=f"[task_repo] Failed to get task: {str(e)}")

    async def update_progress(self, task_id: str, percent: int, log_line: str) -> bool:
        """原子追加进度与日志"""
        lua = """
        local key = KEYS[1]
        local pct = tonumber(ARGV[1])
        local log = ARGV[2]
        local now = ARGV[3]
        local prog = redis.call('HGET', key, 'progress')
        if not prog then return 0 end
        local obj = cjson.decode(prog)
        obj.percent = pct
        table.insert(obj.log, log)
        redis.call('HSET', key, 'progress', cjson.encode(obj))
        redis.call('HSET', key, 'updated_at', now)
        return 1
        """
        ok = await self.redis.eval(lua, 1, f"task:{task_id}", percent, log_line, int(time.time()))
        return bool(ok)

    async def push_plan(self, task_id: str, plan: List[PlanStep]) -> bool:
        """Agent2 写 plan，并发布到 plan_channel"""
        try:
            lua = """
            local key = KEYS[1]
            local pl = ARGV[1]          -- plan JSON
            local now = ARGV[2]

            -- 1. 状态校验
            if redis.call('HGET', key, 'status') ~= 'pending' then
                return 0
            end

            -- 2. 写 plan
            redis.call('HSET', key, 'plan', pl)

            -- 3. 生成 execution 数组（与 plan 一一对应）
            local planObj = cjson.decode(pl)
            local execArr = {}
            for i = 1, #planObj do
                local step = planObj[i]
                execArr[i] = {
                    id          = step.id,
                    step_status = "pending",
                    log         = {os.date("%Y-%m-%d %H:%M:%S").." [INFO] 随plan创建初始化"}
                }
            end
            redis.call('HSET', key, 'execution', cjson.encode(execArr))

            -- 4. 改状态 & 时间戳
            redis.call('HSET', key, 'status', 'planning')
            redis.call('HSET', key, 'updated_at', now)

            return 1
            """

            # 将 plan 转换为 JSON
            plan_data = json.dumps([p.dict() for p in plan], ensure_ascii=False)

            # 执行 Redis Lua 脚本
            ok = await self.redis.eval(lua, 1, f"task:{task_id}", plan_data, int(time.time()))
            if ok:
                # 发布计划到计划频道，通知计划制定完成
                await self.redis.publish("plan_channel", task_id)
                print(f"[TaskRepo] Plan for task {task_id} pushed and published to plan_channel")
                return True
            else:
                print(f"[TaskRepo] Failed to push plan for task {task_id}")
                return False
        except Exception as e:
            print(f"[TaskRepo] Error in push_plan: {e}")
            return False





def create_repo(redis_url: str = "redis://localhost") -> TaskRepo:
    repo = TaskRepo(redis_url)
    # res = repo.redis.ping()  # 预热线程池
    # if not res:
    #     raise ConnectionError("Failed to connect to Redis [task_repo:create_repo]")
    return repo

async def create_repo_sync(redis_url: str = "redis://localhost") -> TaskRepo:
    repo = TaskRepo(redis_url)
    await repo.redis.ping()  # 预热线程池
    return repo