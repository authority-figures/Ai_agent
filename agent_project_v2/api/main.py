# api/main.py
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from api.routers.graph_info import router as graph_router
from api.routers.task_info import router as task_router
from api.routers.task_info import get_task_repo
from fastapi.middleware.cors import CORSMiddleware
from core.service_locator import ServiceLocator




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


pass