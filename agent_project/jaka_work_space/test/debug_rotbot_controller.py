from agent_project.jaka_work_space.robot_controller import *
import numpy as np

def debug_run_path():
    robot_server = RobotServer(ip="192.168.1.10")
    path = np.load("/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_data/interpolate_path.npy")
    robot_server.login()
    robot_server.power_on()
    robot_server.enable_robot()
    robot_server.joint_move(path[0],speed=10)


if __name__ == '__main__':
    pass