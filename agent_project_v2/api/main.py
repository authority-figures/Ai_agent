# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.graph_info import router as graph_router

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




# 可选：根路径的简单响应
@app.get("/")
async def root():
    return {"message": "Agent System API is running"}