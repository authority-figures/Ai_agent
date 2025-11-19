from execution.simulation.environment import SimulationEnvironment
import asyncio
import pybullet as p
import websockets
import json
import time

class DigitalTwinEnv(SimulationEnvironment):
    def __init__(self, options: str = ""):
        super().__init__(options)
        self._last_robot_status = None  # 存储机械臂的最新状态
        # 用于仿真循环控制打印频率
        self._last_status_check_time = 0  # 记录上次打印的时间
        self._status_check_interval = 20  # 如果 5 秒内没有收到状态，才打印一次

    async def update_robot_in_simulation(self):
        """
        订阅并更新仿真中的机器人关节角度。
        假设已经通过 WebSocket 或事件总线获得了最新的机械臂状态
        """
        if self._last_robot_status is None:
            current_time = time.time()
            # 只有在第一次没有收到状态时或者超过设定的检查间隔才打印日志
            if current_time - self._last_status_check_time > self._status_check_interval:
                print("[DigitalTwinEnv] No robot status available yet.")
                self._last_status_check_time = current_time
            return

        # 从 _last_robot_status 中获取最新的机械臂关节角度
        joint_positions = self._last_robot_status[19]

        if joint_positions is None:
            print("[DigitalTwinEnv] No joint positions in robot status.")
            return

        # 更新仿真中的机器人
        if not (self.robot_list and len(self.robot_list) > 0):
            print("[DigitalTwinEnv] No robots in simulation to update.")
            return
        for i, joint_position in enumerate(joint_positions):
            p.resetJointState(self.robot_list[0].id_robot, i, joint_position, physicsClientId=self.physics_client)

    async def start_subscribe(self):
        """启动订阅机器人状态并更新仿真机器人"""
        # 假设你有一个 WebSocket 或者其他订阅机制将状态推送到 _last_robot_status
        # 我们模拟这种推送，通过定期调用 update_robot_in_simulation 来同步状态
        try:
            while self.is_running:
                # 调用方法更新仿真中的机器人状态
                await self.update_robot_in_simulation()
                await asyncio.sleep(0.01)  # 每0.1秒检查一次状态并更新
        except Exception as e:
            print(f"[DigitalTwinEnv] Error during subscription: {e}")


    def start_simulation(self, real_time=True):
        """启动仿真并启动状态订阅"""
        super().start_simulation(real_time)  # 调用父类的启动仿真方法
        # 启动订阅机器人状态并更新仿真
        asyncio.create_task(self.start_subscribe())

    def stop_simulation(self):
        """停止仿真"""
        super().stop_simulation()  # 停止仿真
        self.is_running = False  # 停止订阅






