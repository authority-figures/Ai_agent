'''

用于在单独的进程中运行PyBullet仿真环境的模块
'''



from PyQt5.QtCore import QThread, QTimer
import time
import asyncio
from core.simulation_request import *

# 为PyBullet窗口设置唯一的名称
PYBULLET_WINDOW_NAME = "MyDigitalTwinSimulation_" + str(int(time.time()))

class DigitalTwinProcess(QThread):
    """运行PyBullet仿真的线程"""

    def __init__(self):
        super().__init__()
        self.running = True
        # self.env = SimulationEnvironment(options=f"--window_title={PYBULLET_WINDOW_NAME} --width=800 --height=600")
        self.env = CustomDigitalTwinEnv()
        # self.env.initialize()
        self.loop = asyncio.new_event_loop()
        self.env_title = PYBULLET_WINDOW_NAME


    def run(self):
        # self.env.is_running = True

        asyncio.set_event_loop(self.loop)  # 设置当前事件循环
        # self.loop.run_until_complete(self.env.initialize())  # 初始化环境，异步执行
        self.loop.run_forever()  # 运行事件循环（保持异步任务持续执行）
        # self.env.start_simulation()

    def stop(self):
        # self.running = False
        self.env.stop_simulation()




import httpx

class CustomDigitalTwinEnv:
    def __init__(self, base_url="http://localhost:8003"):
        self.base_url = base_url
        self.reference_frame = "body"

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

    async def get_tcp_pos_and_ori(self,):
        async with httpx.AsyncClient() as client:
            try:
                request = GetPosOriRequest(object_id=None, reference_frame=self.reference_frame)
                response = await client.post(f"{self.base_url}/get_tcp_pos_and_ori", json=request.to_dict())
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to get_tcp_pos_and_ori"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def get_robot_end_effector_pos_and_ori(self, ):
        async with httpx.AsyncClient() as client:
            try:
                request = GetPosOriRequest(object_id=None, reference_frame=self.reference_frame)
                response = await client.post(f"{self.base_url}/get_robot_end_pos_and_ori", json=request.to_dict())
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to get_robot_end_effector_pos_and_ori"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def set_robot_end_pos_and_ori(self, target_position, target_orientation, maxVelocity=1):
        try:
            request = {
                "robot_id": None,
                "target_position": target_position,
                "target_orientation": target_orientation,
                "reference_frame": self.reference_frame,
                "maxVelocity": maxVelocity
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/move_robot_to_target", json=request,timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to set_robot_end_pos_and_ori"}
        except Exception as e:
            print(f"[CustomSimulationEnv:set_robot_end_pos_and_ori] Exception: {e}")
            return {"status": "error", "message": str(e)}

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

    async def subscribe_machine_state(self, on_subscribe):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/publish_machine_state", json={"on_subscribe": on_subscribe})
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to subscribe_machine_state"}

    async def get_machine_axis_state(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/get_machine_axis_state")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to get_machine_axis_state"}

    async def update_machine_axis_state(self, axis_values, maxVelocity=1):
        request = MachineAxisRequest(target_axis_values=axis_values, maxVelocity=maxVelocity)
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/update_machine_axis_state", json=request.to_dict(), timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to update_machine_axis_state"}

    async def start_machine_axis_tcp_server(self, host="127.0.0.1", port=9101):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/start_machine_axis_tcp_server", json={"host": host, "port": port})
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to start_machine_axis_tcp_server"}

    async def stop_machine_axis_tcp_server(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/stop_machine_axis_tcp_server")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Failed to stop_machine_axis_tcp_server"}


