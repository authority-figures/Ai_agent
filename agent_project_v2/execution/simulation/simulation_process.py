'''

用于在单独的进程中运行PyBullet仿真环境的模块
'''


import multiprocessing as mp
import pybullet as p
import pybullet_data
from execution.simulation.environment import SimulationEnvironment
from PyQt5.QtCore import QThread, QTimer
import time
import asyncio

# 为PyBullet窗口设置唯一的名称
PYBULLET_WINDOW_NAME = "MyPyBulletSimulation_" + str(int(time.time()))

class PyBulletProcess(QThread):
    """运行PyBullet仿真的线程"""

    def __init__(self):
        super().__init__()
        self.running = True
        # self.env = SimulationEnvironment(options=f"--window_title={PYBULLET_WINDOW_NAME} --width=800 --height=600")
        self.env = CustomSimulationEnv()
        # self.env.initialize()
        self.loop = asyncio.new_event_loop()
        self.env_title = PYBULLET_WINDOW_NAME

    def run(self):
        # self.env.is_running = True

        asyncio.set_event_loop(self.loop)  # 设置当前事件循环
        self.loop.run_until_complete(self.env.initialize())  # 初始化环境，异步执行
        self.loop.run_forever()  # 运行事件循环（保持异步任务持续执行）
        self.env.start_simulation()

    def stop(self):
        # self.running = False
        self.env.stop_simulation()




import httpx

class CustomSimulationEnv:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url

    async def start_simulation(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/start_simulation")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to start simulation"}

    async def stop_simulation(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/stop_simulation")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to stop simulation"}

    async def initialize(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/init_env")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to initialize environment"}

    async def clear_env(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/clear_env")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to clear environment"}

    async def load_scene(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/load_scene")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to load scene"}

    async def show_axis(self, ifshow):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/show_axis", json={"ifshow": ifshow})
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to show axis"}

    async def add_object(self, urdf_path, basePosition, baseOrientation, useFixedBase):
        data = {
            "urdf_path": urdf_path,
            "basePosition": basePosition,
            "baseOrientation": baseOrientation,
            "useFixedBase": useFixedBase
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/add_object", json=data)
            return response.json()

    async def move_robot(self, robot_id, joint_positions):
        data = {
            "robot_id": robot_id,
            "joint_positions": joint_positions
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/move_robot", json=data)
            return response.json()

    async def get_robot_end_pos_and_ori(self, robot_id):
        data = {"robot_id": robot_id}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/get_robot_end_pos_and_ori", json=data)
            return response.json()


    async def show_tcp_axis(self, ifshow):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/show_tcp_axis", json={"ifshow": ifshow})
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Failed to show axis"}
