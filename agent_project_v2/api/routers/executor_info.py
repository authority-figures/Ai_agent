import asyncio
import aioredis
from fastapi import APIRouter, HTTPException, Depends
from core.service_locator import ServiceLocator
from agent.services.agent_service import AgentService
from agent.services.agent_service import AgentService
from core.service_locator import ServiceLocator
from agent.graph.executor_graph import session1_config




router = APIRouter(prefix="/api/executor", tags=["Executor Information"])

# 全局变量以确保引用不被GC回收
redis_client = None
pubsub = None
listener_task = None
executor_lock = asyncio.Lock()  # 锁，用于串行执行任务


def get_agent_service():
    agent_service = ServiceLocator.get('executor_agent_service')
    if agent_service is None:
        raise HTTPException(status_code=500, detail="Executor service not available")
    return agent_service


async def executor_listener(executor_service: AgentService):
    """
    异步监听 Redis 中的 plan_channel，一旦有新的计划任务被制定，执行任务。
    """
    global pubsub

    while True:
        try:
            print("[ExecutorAgent] Listening for new plans...")
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    task_id = msg["data"]
                    print(f"[ExecutorAgent] Received new plan from task: {task_id}")

                    # 使用锁确保任务串行执行
                    async with executor_lock:
                        # 任务串行执行
                        await executor_service.compiled_graph.ainvoke({
                            "input": "null",
                            "task_id": str(task_id),
                            "input_type": "run_plan",
                        }, config=session1_config)

        except (asyncio.CancelledError, GeneratorExit):
            print("[ExecutorAgent] Listener cancelled, exiting gracefully...")
            break
        except Exception as e:
            print(f"[ExecutorAgent] Error: {e}, retrying in 3 seconds...")
            await asyncio.sleep(3)


@router.on_event("startup")
async def startup_event():
    """
    FastAPI 启动时运行：初始化 Redis 并启动监听任务。
    """
    global redis_client, pubsub, listener_task

    print("[System] Starting ExecutorAgent listener...")

    # 获取 executor service
    executor_service = ServiceLocator.get("executor_agent_service")
    if not executor_service:
        raise RuntimeError("Executor service not registered")

    # 初始化 Redis 客户端
    redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("plan_channel")

    # ✅ 在当前事件循环中启动监听任务
    loop = asyncio.get_running_loop()
    listener_task = loop.create_task(executor_listener(executor_service))
    print("[System] ExecutorAgent listener started successfully.")


@router.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI 关闭时运行：取消监听任务并关闭 Redis。
    """
    global redis_client, pubsub, listener_task
    print("[System] Shutting down ExecutorAgent listener...")

    # 取消后台任务
    if listener_task:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    # 关闭 Redis 连接
    if pubsub:
        await pubsub.unsubscribe("plan_channel")
        await pubsub.close()
    if redis_client:
        await redis_client.close()

    print("[System] ExecutorAgent listener stopped cleanly.")