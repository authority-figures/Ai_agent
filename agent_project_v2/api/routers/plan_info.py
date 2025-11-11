import asyncio
import aioredis
from fastapi import APIRouter, HTTPException, Depends
from core.service_locator import ServiceLocator
from agent.services.agent_service import AgentService
from core.service_locator import ServiceLocator
from agent.graph.plan_graph import session1_config


router = APIRouter(prefix="/api/plan", tags=["plan Information"])

# 全局变量以确保引用不被GC回收
redis_client = None
pubsub = None
listener_task = None


def get_agent_service():
    agent_service = ServiceLocator.get('plan_agent_service')
    if agent_service is None:
        raise HTTPException(status_code=500, detail="Agent service not available")
    return agent_service


async def plan_agent_listener(agent_service: AgentService):
    """
    异步监听 Redis 中的 task_channel，一旦有新任务，调用 plan_agent 的 Graph。
    """
    global pubsub

    while True:
        try:
            print("[PlanAgent] Listening for new tasks...")
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    task_id = msg["data"]

                    # 检查该任务是否已经被处理
                    task_processed = await redis_client.get(f"task_processed:{task_id}")
                    if task_processed:
                        # 如果任务已经处理过，跳过该任务
                        print(f"[PlanAgent] Task {task_id} already processed, skipping.")
                        continue

                    print(f"[plan_info:plan_agent_listener:PlanAgent] Received new task: {task_id}")
                    asyncio.create_task(agent_service.compiled_graph.ainvoke({
                        "input": "null",
                        "task_id": str(task_id),
                        "input_type": "run_task",
                         },config=session1_config))

                    # 将任务标记为已处理，避免重复触发
                    await redis_client.set(f"task_processed:{task_id}", "true", ex=86400)  # 设置 1 天的过期时间

        except (asyncio.CancelledError, GeneratorExit):
            print("[plan_info:plan_agent_listener:PlanAgent] Listener cancelled, exiting gracefully...")
            break
        except Exception as e:
            print(f"[plan_info:plan_agent_listener:PlanAgent] Error: {e}, retrying in 3 seconds...")
            await asyncio.sleep(3)


@router.on_event("startup")
async def startup_event():
    """
    FastAPI 启动时运行：初始化 Redis 并启动监听任务。
    """
    global redis_client, pubsub, listener_task

    print("[System] Starting PlanAgent listener...")

    # 获取 agent service
    agent_service = ServiceLocator.get("plan_agent_service")
    if not agent_service:
        raise RuntimeError("PlanAgent service not registered")

    # 初始化 Redis 客户端
    redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("task_channel")

    # ✅ 在当前事件循环中启动监听任务
    loop = asyncio.get_running_loop()
    listener_task = loop.create_task(plan_agent_listener(agent_service))
    print("[System] PlanAgent listener started successfully.")


@router.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI 关闭时运行：取消监听任务并关闭 Redis。
    """
    global redis_client, pubsub, listener_task
    print("[System] Shutting down PlanAgent listener...")

    # 取消后台任务
    if listener_task:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    # 关闭 Redis 连接
    if pubsub:
        await pubsub.unsubscribe("task_channel")
        await pubsub.close()
    if redis_client:
        await redis_client.close()

    print("[System] PlanAgent listener stopped cleanly.")