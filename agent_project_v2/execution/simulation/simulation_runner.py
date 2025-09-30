import threading
import time
import pybullet as p
import pybullet_data
from agent_project.simulation.environment import SimulationEnvironment
from agent_project.simulation.api import start_api_server,sim_env


def run_simulation():
    """
    运行仿真环境的主线程，维持仿真步进循环
    """
    # sim_env = SimulationEnvironment()
    sim_env.initialize()

    while sim_env.running:
        sim_env.step_simulation()
        time.sleep(sim_env.time_step)  # 控制仿真步进时间

if __name__ == "__main__":
    # 启动仿真环境线程
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()

    # 启动 API 服务器，允许外部控制仿真
    start_api_server()
