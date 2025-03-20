# api_server.py
from fastapi import FastAPI, HTTPException
from models import *
import uvicorn

# 引入你定义的 RobotServer，但是此处我们只声明类型，不直接实例化。
from robot_controller import RobotServer

# 用于保管 robot_server 实例的全局变量（或其他更优雅的方式）
robot_server: RobotServer = None



# 创建 FastAPI 应用
app = FastAPI()

# 对外暴露一个函数，用于将 RobotServer 注入
def set_robot_server(server: RobotServer):
    global robot_server
    robot_server = server

# 然后写若干路由示例
@app.post("/login")
def login_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.login()
    if ret[0] == 0:
        return {"status": "ok", "detail": f"Login success on IP {robot_server.ip}"}
    else:
        raise HTTPException(status_code=500, detail=f"Login failed: {ret[0]}")

@app.post("/logout")
def logout_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.logout()
    if ret[0] == 0:
        return {"status": "ok", "detail": "Logout success"}
    else:
        raise HTTPException(status_code=500, detail=f"Logout failed: {ret[0]}")

@app.post("/power_on")
def power_on_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.power_on()
    if ret[0] == 0:
        return {"status": "ok", "detail": "Power on success"}
    else:
        raise HTTPException(status_code=500, detail=f"Power on failed: {ret[0]}")

@app.post("/power_off")
def power_off_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.power_off()
    if ret[0] == 0:
        return {"status": "ok", "detail": "Power off success"}
    else:
        raise HTTPException(status_code=500, detail=f"Power off failed: {ret[0]}")

@app.post("/enable_robot")
def enable_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.enable_robot()
    if ret[0] == 0:
        return {"status": "ok", "detail": "Enable robot success"}
    else:
        raise HTTPException(status_code=500, detail=f"Enable robot failed: {ret[0]}")

@app.post("/disable_robot")
def disable_robot():
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.disable_robot()
    if ret[0] == 0:
        return {"status": "ok", "detail": "Disable robot success"}
    else:
        raise HTTPException(status_code=500, detail=f"Disable robot failed: {ret[0]}")
    


@app.post("/move_line")
def move_line_api(params: MoveParams):
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    position = [params.x, params.y, params.z, params.rx, params.ry, params.rz]
    ret = robot_server.move_line(position, 50, 50)
    if ret[0] == 0:
        return {"status": "ok", "detail": f"Moved to {position}"}
    else:
        raise HTTPException(status_code=500, detail=f"Move failed: {ret[0]}")

@app.post("/joint_move")
def joint_move_api(params: JointMoveParams):
    if not robot_server:
        raise HTTPException(status_code=500, detail="RobotServer not set.")
    ret = robot_server.joint_move(params.joint_position, params.move_mode, params.speed, params.acc, params.is_block, params.tol)
    if ret[0] == 0:
        return {"status": "ok", "detail": f"Moved to {params.joint_position}"}
    else:
        raise HTTPException(status_code=500, detail=f"Move failed: {ret[0]}")


def start_api_server():
    """ 启动 API 服务器 """
    uvicorn.run(app, host="127.0.0.1", port=8002)
