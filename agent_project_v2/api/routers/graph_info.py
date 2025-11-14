# api/graph_info.py (或类似名称)
from fastapi import APIRouter, HTTPException, Depends
from core.service_locator import ServiceLocator
from agent.services.agent_service import AgentService
from agent.graph.Interactive_chat_graph import session1_config
import asyncio
import aioredis

router = APIRouter(prefix="/api/graph", tags=["Graph Information"])

def get_agent_service():
    agent_service = ServiceLocator.get('agent_service')
    if agent_service is None:
        raise HTTPException(status_code=500, detail="Agent service not available")
    return agent_service



# 全局变量以确保引用不被GC回收
redis_client = None
pubsub = None
listener_task = None
executor_lock = asyncio.Lock()  # 锁，用于串行执行任务

async def interactive_listener(interactive_service: AgentService):
    """
    异步监听 Redis 中的 plan_channel，一旦有新的计划任务被制定，执行任务。
    """
    global pubsub

    while True:
        try:
            print("[InteractiveAgent] Listening for new finished task...")
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    task_id = msg["data"]
                    print(f"[InteractiveAgent] Received new finished task: {task_id}")

                    # 使用锁确保任务串行执行
                    async with executor_lock:
                        # 任务串行执行
                        await interactive_service.compiled_graph.ainvoke({
                            "input": "null",
                            "task_id": str(task_id),
                            "input_type": "finished_task_channel",
                            "finished_task_id": str(task_id)
                        }, config=session1_config)

        except (asyncio.CancelledError, GeneratorExit):
            print("[Graph_info:interactive_listener:InteractiveAgent] Listener cancelled, exiting gracefully...")
            break
        except Exception as e:
            print(f"[Graph_info:interactive_listener:InteractiveAgent] Error: {e}, retrying in 3 seconds...")
            await asyncio.sleep(3)





@router.get("/graph-structure")
async def get_graph_structure(agent_service: AgentService = Depends(get_agent_service)):
    """
    获取Agent图结构的API端点。
    """
    try:
        graph_data = agent_service.get_graph_structure()
        return {
            "status": "success",
            "data": graph_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph structure: {str(e)}")

@router.get("/invoke")
async def invoke_graph(user_input: str, agent_service: AgentService = Depends(get_agent_service)):
    """
    调用Agent图的API端点。
    """
    try:
        result = await agent_service.invoke_graph(user_input)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[graph_info:invoke_graph] Failed to invoke graph: {str(e)}")




# @router.on_event("startup")
async def startup_event():
    """
    FastAPI 启动时运行：初始化 Redis 并启动监听任务。
    """
    global redis_client, pubsub, listener_task

    print("[System] Starting ExecutorAgent listener...")

    # 获取 executor service
    interactive_service = ServiceLocator.get("agent_service")
    if not interactive_service:
        raise RuntimeError("Executor service not registered")

    # 初始化 Redis 客户端
    redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("finished_task_channel")

    # ✅ 在当前事件循环中启动监听任务
    loop = asyncio.get_running_loop()
    listener_task = loop.create_task(interactive_listener(interactive_service))
    print("[System] InteractiveAgent listener started successfully.")