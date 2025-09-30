import numpy as np
import pylab as p

from agent_project.simulation.environment import *
from agent_project.simulation.calibrator import *




def debug_interpolate_joint_path():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 0, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.4, 0.4, 0.005, 0])
    # sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # # workpiece:C_continue
    # sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
    #                                     [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
    #                                     childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))
    # workpiece:dada
    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.02, -0.06 + 0.0125, 0.05 - 0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))

    calibration_data = np.load('/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/datas/calibration_data.npz',allow_pickle=True)
    sim_env.calibration_from_data(calibration_data)


    import threading
    def run_simulation():
        while True:
            if sim_env.running:
                sim_env.step_simulation()
                # sim_env.robot_list[0].show_link_sys(7, -1, 1)
                time.sleep(sim_env.time_step)  # 控制仿真步进时间
                sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
                sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
                sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
                sim_env.camera.show_link_sys(3, -1, 1, name="camera")
                if sim_env.camera_open == True:
                    sim_env.rm_sys.update_cam_pos()
            else:
                time.sleep(0.1)

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    sim_env.update_workpiece2robotBy_calibration()
    sim_env.update_robot_constrain()
    sim_env.update_camera_constrain()
    sim_env.running = False
    cam_dist = 0.0
    pos, ori = sim_env.rm_sys.get_point_in_workpiece2robot((0.02 + cam_dist, -0.06 + 0.0125, 0.05 - 0.0125),
                                                           (0.0005629,0.706825,0.707388,0.0005633))
    pos, ori = sim_env.rm_sys.get_point_in_workpiece2robot((-0.004, -0.00 , 0.05 + 0.03),
                                                           (0.0005629, 0.706825, 0.707388, 0.0005633))
    start = [3.4,0,0,0,0,0]
    goal = sim_env.robot_list[0].get_state_from_ik(pos,ori,start=start,tcp_name='rolling_tool')


    # sim_env.robot_list[0].joint_move(joints)
    sim_env.running = True
    time.sleep(2)
    sim_env.running = False

    # 执行规划
    sim_env.pb_ompl_interface.get_T_goal(goal, tcp_name="rolling_tool")
    sim_env.pb_ompl_interface.z_range = (0.001, 0.1)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.02, 0.02)
    sim_env.pb_ompl_interface.y_range = (-0.02, 0.02)
    sim_env.pb_ompl_interface.yaw_range = 10
    sim_env.pb_ompl_interface.roll_range = 2
    sim_env.pb_ompl_interface.pitch_range = 2

    sim_env.pb_ompl_interface.set_tsRRT_sample()
    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # sim_env.pb_ompl_interface.set_state_sampler(taskspaceRRT.MixedValidStateSampler(sim_env.pb_ompl_interface.si, sim_env.pb_ompl_interface.sample_in_task_space, ratio=0.8))
    res, path = sim_env.pb_ompl_interface.plan_start_goal(start, goal)
    np.save(r'/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/datas/insert_path.npy', path)
    print('success save')
    sim_env.camera_open=False
    sim_env.running = True
    sim_env.pb_ompl_interface.execute(path)



    pass



if __name__ == '__main__':

    debug_interpolate_joint_path()
