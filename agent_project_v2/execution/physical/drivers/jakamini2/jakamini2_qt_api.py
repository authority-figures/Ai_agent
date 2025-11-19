
import time
import asyncio
from core.simulation_request import *
import httpx
class Jakamini2QtApi:
    def __init__(self, base_url="http://localhost:8002"):
        self.base_url = base_url

    async def connect(self,ip):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/connect",json={"ip": ip}, timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to connect"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:connect] Error connecting to robot:", e)
            return {"status": "error", "message": str(e)}

    async def disconnect(self,ip):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/disconnect", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to disconnect"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:connect] Error disconnect to robot:", e)
            return {"status": "error", "message": str(e)}


    async def power_on(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/power_on", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to power on"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:power_on] Error powering on robot:", e)
            return {"status": "error", "message": str(e)}

    async def power_off(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/power_off", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to power off"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:power_off] Error powering off robot:", e)
            return {"status": "error", "message": str(e)}



    async def enable_robot(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/enable_robot", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to enable robot"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:enable_robot] Error enabling robot:", e)
            return {"status": "error", "message": str(e)}


    async def disable_robot(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/disable_robot", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to disable robot"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:disable_robot] Error disabling robot:", e)
            return {"status": "error", "message": str(e)}


    async def start_subscribe(self):
        try:
            async with httpx.AsyncClient() as client:
                response1 = await client.post(f"{self.base_url}/start_subscribe", timeout=10)
                response2 = await client.post(f"http://localhost:8003/start_listening_robot_status", timeout=10)
                if response1.status_code == 200 and response2.status_code == 200:
                    return response1.json(), response2.json()
                else:
                    return {"status": "error", "message": "Failed to start subscribe"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:start_subscribe] Error starting subscribe:", e)
            return {"status": "error", "message": str(e)}

    async def stop_subscribe(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/stop_subscribe", timeout=10)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": "Failed to stop subscribe"}
        except Exception as e:
            print("[jakamini2_qt_api:Jakamini2QtApi:stop_subscribe] Error stopping subscribe:", e)
            return {"status": "error", "message": str(e)}



    def send_command(self, command: str) -> str:
        """
        Send a command to the Jaka Mini 2 robot and receive a response.

        :param command: The command string to send to the robot.
        :return: The response from the robot.
        """
        # Implementation of command sending logic using Qt API
        pass