# api/main.py
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from api.routers.graph_info import router as graph_router
from api.routers.task_info import router as task_router
from api.routers import plan_info
from api.routers import executor_info
from api.routers import graph_info
from api.routers.task_info import get_task_repo
from fastapi.middleware.cors import CORSMiddleware
from core.service_locator import ServiceLocator
import asyncio

# pybullet相关-----------------------------------
import multiprocessing as mp
from api.routers.physical_info import run_physical_executor_service
from api.routers.pybullet_info import run_pybullet_service




# 创建 FastAPI 应用实例
app = FastAPI(title="Agent System API", version="0.1.0")

# 配置 CORS 中间件 - 允许你的 PyQt 前端应用（或其他Web前端）调用 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应更严格地设置
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含 API 路由
app.include_router(graph_router)   # 注册图结构相关的路由
app.include_router(task_router)    # 注册任务相关的路由

# 定义全局变量来存储PyBullet仿真进程
pybullet_proc = None
physical_proc = None
# 可选：根路径的简单响应
@app.get("/")
async def root():
    return {"message": "Agent System API is running"}


# 创建websocket用于向前端推送实时更新
active_connections = set()
@app.websocket("/ws/state")
async def state_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # 保持连接，忽略接受
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("WebSocket disconnected")


try:
    agent_service = ServiceLocator.get('agent_service')
    if agent_service:
        agent_service.set_connection_pool(active_connections)
    else:
        print("AgentService not found in ServiceLocator.")
except Exception as e:
    print(f"Error sending state to AgentService: {e}")


try:
    task_repo = ServiceLocator.get('task_repo')
    if task_repo:
        print("TaskRepo found in ServiceLocator.")
        pass
    else:
        print("TaskRepo not found in ServiceLocator.")
except Exception as e:
    print(f"Error sending state to TaskRepo: {e}")


# 在 FastAPI 启动时注册
# @app.on_event("startup")
# async def startup_event():
#     # 启动 plan_agent_listener 协程，不阻塞主事件循环
#     asyncio.create_task(plan_agent_listener())
#
#     print("Startup event completed.")

@app.on_event("startup")
async def startup_event():
    # 启动plan agentd的监听
    await plan_info.startup_event()
    await executor_info.startup_event()
    await graph_info.startup_event()

    # 启动PyBullet仿真进程
    pybullet_proc = mp.Process(target=run_pybullet_service)
    pybullet_proc.start()
    print("[Fast api:main] PyBullet simulation started.")

    # 启动physical真实机械臂控制进程
    physical_proc = mp.Process(target=run_physical_executor_service)
    physical_proc.start()
    print("[Fast api:main] Physical simulation started.")


@app.on_event("shutdown")
async def shutdown_event():
    await plan_info.shutdown_event()
    await executor_info.shutdown_event()

    # 停止PyBullet仿真进程
    print("Shutting down PyBullet simulation.")
    # 如果使用多进程管理PyBullet，确保在这里终止PyBullet进程
    # 这里可以通过共享的信号或 IPC 机制来停止 PyBullet 进程
    if pybullet_proc:
        pybullet_proc.terminate()
        print("PyBullet simulation stopped.")
    if physical_proc:
        physical_proc.terminate()
        print("Physical simulation stopped.")




