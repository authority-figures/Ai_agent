from fastapi import FastAPI
from routes.simulation_routes import router as simulation_router
from routes.robotics_routes import router as robotics_router

# 创建 FastAPI 服务器
app = FastAPI(title="Agent API Server", version="1.0")

# 注册路由
app.include_router(simulation_router, prefix="/simulation", tags=["Simulation"])
app.include_router(robotics_router, prefix="/robotics", tags=["Robotics"])

@app.get("/")
async def root():
    return {"message": "Agent API Server is running"}

# 运行服务器（仅用于调试）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
