
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



    def send_command(self, command: str) -> str:
        """
        Send a command to the Jaka Mini 2 robot and receive a response.

        :param command: The command string to send to the robot.
        :return: The response from the robot.
        """
        # Implementation of command sending logic using Qt API
        pass