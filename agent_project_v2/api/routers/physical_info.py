import asyncio

import uvicorn
import numpy as np
import threading
import time
from fastapi import FastAPI,Request
from pydantic import BaseModel
from execution.physical.drivers.jakamini2.driver import *
from core.physical_request import *
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

# 创建 FastAPI 服务器
app = FastAPI(title="Physical System API", version="0.1.0")

physical_driver = Jakamini2Driver('192.168.100.20')
physical_driver.init_sim()
print("physical_driver physicsClientId:", physical_driver.physics_client)
# physical_driver = None



@app.websocket("/ws/robot_status")
async def websocket_robot_status(ws: WebSocket):
    await ws.accept()
    print("[ws] client connected")

    # 用于检测状态变化，避免重复发送
    last_sent = None

    try:
        while True:
            # 如果还没连接机器人，可以发一个提示或空状态
            if not physical_driver.connected or physical_driver._last_status is None:
                await ws.send_json({
                    "status": "no_data",
                    "message": "Robot not connected or no status yet"
                })
                await asyncio.sleep(0.5)
                continue

            current = physical_driver._last_status

            # 这里简单做一下“变化检测”，也可以直接每隔 100ms 发一次 current
            if current != last_sent:
                await ws.send_json({
                    "status": "ok",
                    "data": current,
                })
                last_sent = current

            await asyncio.sleep(0.01)  # 推送频率

    except WebSocketDisconnect:
        print("[ws] client disconnected")
    except Exception as e:
        print(f"[ws] Error in websocket_robot_status: {e}")



@app.post("/connect")
async def connect(request:Request):
    """ API: 启动仿真环境 """
    try:
        request_data = await request.json()
        ip = request_data.get("ip", None)  # 从解析后的字典中获取 ip
        ret = await physical_driver.connect(ip=ip)
        if ret[0] == 0:
            return {"status": "success"}
        else:
            return {"status": "failed", "message": ret[1]}
    except Exception as e:
        print("[execution:physical:api:connect] Error starting connection:", e)
        return {"status": "error", "message": str(e)}


@app.post("/disconnect")
async def disconnect():
    """ API: 启动仿真环境 """
    try:
        ret = await physical_driver.disconnect()
        if ret[0]==0:
            return {"status": "success"}
        else:
            return {"status": "failed", "message": ret[1]}
    except Exception as e:
        print("[execution:physical:api:disconnect] Error close connection:", e)
        return {"status": "error", "message": str(e)}


@app.post("/power_on")
async def power_on():
    """ API: 启动仿真环境 """
    try:
        ret = await physical_driver.power_on()
        if ret[0] == 0:
            return {"status": "success"}
        else:
            return {"status": "failed", "message": ret[1]}
    except Exception as e:
        print("[execution:physical:api:power_on] Error power_on:", e)
        return {"status": "error", "message": str(e)}

@app.post("/power_off")
async def power_off():
    """ API: 启动仿真环境 """
    try:
        ret = await physical_driver.power_off()
        if ret[0] == 0:
            return {"status": "success"}
        else:
            return {"status": "failed", "message": ret[1]}
    except Exception as e:
        print("[execution:physical:api:power_off] Error power_off:", e)
        return {"status": "error", "message": str(e)}


@app.post("/enable_robot")
async def enable_robot():
    """ API: 启动仿真环境 """
    try:
        await physical_driver.enable_robot()
        return {"status": "success"}
    except Exception as e:
        print("[execution:physical:api:enable_robot] Error enable_robot:", e)
        return {"status": "error", "message": str(e)}


@app.post("/disable_robot")
async def disable_robot():
    """ API: 启动仿真环境 """
    try:
        await physical_driver.disable_robot()
        return {"status": "success"}
    except Exception as e:
        print("[execution:physical:api:disable_robot] Error disable_robot:", e)
        return {"status": "error", "message": str(e)}

@app.post("/get_joint_pos")
async def get_joint_pos():
    """ API: 启动仿真环境 """
    try:
        joint_pos = await physical_driver.get_joint_pos()
        if joint_pos is not None:
            return {"status": "success", "message": joint_pos}
        return {"status": "failed", "message": []}
    except Exception as e:
        print("[execution:physical:api:get_joint_pos] Error get_joint_pos:", e)
        return {"status": "error", "message": str(e)}


@app.post("/joint_move")
async def joint_move(request:JointMoveRequest):
    """ API: 启动仿真环境 """
    try:
        joint_pos = await physical_driver.joint_move(
            joint_positions=request.joint_positions,
            move_mode=request.move_mode,
            speed=request.speed,
            acc=request.acc,
            is_block=request.is_block,
            tol=request.tol
        )
        if joint_pos is not None:
            return {"status": "success", "message": joint_pos}
        return {"status": "failed", "message": []}
    except Exception as e:
        print("[execution:physical:api:joint_move] Error joint_move:", e)
        return {"status": "error", "message": str(e)}



@app.post("/start_subscribe")
async def start_subscribe():
    """ API: 启动仿真环境 """
    try:
        if physical_driver.connected:
            physical_driver.start_status_monitor()
            return {"status": "success"}
        else:
            print("[execution:physical:api:start_subscribe] Robot not connected.")
            return {"status": "failed", "message": []}
    except Exception as e:
        print("[execution:physical:api:get_joint_pos] Error get_joint_pos:", e)
        return {"status": "error", "message": str(e)}


@app.post("/stop_subscribe")
async def stop_subscribe():
    """ API: 停止订阅，停止监听机器人状态 """
    try:
        # 停止状态轮询任务
        await physical_driver.stop_status_monitor()
        return {"status": "success"}
    except Exception as e:
        print("[execution:physical:api:stop_subscribe] Error:", e)
        return {"status": "error", "message": str(e)}











def run_physical_executor_service():
    uvicorn.run(app, host="127.0.0.1", port=8002,
                reload=False,
                log_level="info",
                loop="asyncio",
                )  # 设置为8002端口运行
    pass

if __name__ == '__main__':
    run_physical_executor_service()
    pass