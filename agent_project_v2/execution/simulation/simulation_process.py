'''

用于在单独的进程中运行PyBullet仿真环境的模块
'''


import multiprocessing as mp
import pybullet as p
import pybullet_data
from execution.simulation.environment import SimulationEnvironment
from PyQt5.QtCore import QThread, QTimer
import time


# 为PyBullet窗口设置唯一的名称
PYBULLET_WINDOW_NAME = "MyPyBulletSimulation_" + str(int(time.time()))

class PyBulletProcess(QThread):
    """运行PyBullet仿真的线程"""

    def __init__(self):
        super().__init__()
        self.running = True
        self.env = SimulationEnvironment(options=f"--window_title={PYBULLET_WINDOW_NAME} --width=800 --height=600")
        self.env.initialize()
        self.env_title = PYBULLET_WINDOW_NAME

    def run(self):
        # self.env.is_running = True
        self.env.start_simulation()

    def stop(self):
        # self.running = False
        self.env.stop_simulation()