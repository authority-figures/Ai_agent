import numpy as np

from agent_project.simulation.environment import *
from agent_project.simulation.calibrator import *



def use_real_cailbration():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 1, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.5, 0.4, 0.00, 0])
    sim_env.pb_ompl_interface.set_planner("RRTConnect")

    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))

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
                time.sleep(1 / 240.)

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()
    sim_env.update_workpiece2robotBy_calibration()
    sim_env.update_robot_constrain()

def debug_full_cailbration():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 1, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.5, 0.4, 0.00, 0])
    sim_env.pb_ompl_interface.set_planner("RRTConnect")

    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))

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
                time.sleep(1/240.)

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    sim_env.running = True
    cam_dist = 0.08
    pos,ori = sim_env.rm_sys.get_point_in_workpiece2robot((0.0325+cam_dist, -0.072 + 0.0125, 0.05266 - 0.0125),
                                                (0, 0.7071068, 0, -0.7071068))
    joints = sim_env.robot_list[0].get_state_from_ik(pos,ori,tcp_name="RGB_camera")
    sim_env.modify_workpiece_constrain([+0.005,0.1,0.1],[0,0,0,1])
    sim_env.ninePoints_calibration(joints)
    sim_env.update_workpiece2robotBy_calibration()
    sim_env.update_robot_constrain()

    # 执行规划
    target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((0, -0.0, 0.1),
                                                                             (0.0005629, 0.706825, 0.707388, 0.0005633))
    joints = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys[0], target_point_in_robot_sys[1],
                                                     start=None, maxNumIteration=10000, tcp_name="rolling_tool")

    start = sim_env.robot_list[0].reset()
    start = sim_env.robot_list[0].get_cur_state()
    goal = joints

    sim_env.pb_ompl_interface.z_range = (0.01, 0.2)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.01, 0.01)
    sim_env.pb_ompl_interface.y_range = (-0.02, 0.02)
    sim_env.pb_ompl_interface.yaw_range = 10
    sim_env.pb_ompl_interface.roll_range = 5
    sim_env.pb_ompl_interface.pitch_range = 5

    sim_env.pb_ompl_interface.get_T_goal(goal, tcp_name="rolling_tool")
    sim_env.pb_ompl_interface.set_tsRRT_sample()
    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # sim_env.pb_ompl_interface.set_state_sampler(taskspaceRRT.MixedValidStateSampler(sim_env.pb_ompl_interface.si, sim_env.pb_ompl_interface.sample_in_task_space, ratio=0.8))
    sim_env.running = False
    res, path = sim_env.pb_ompl_interface.plan_start_goal(start, goal)
    sim_env.running = True
    if res:
        sim_env.pb_ompl_interface.execute(path, dynamics=True)

def debug_interpolate_joint_path():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [3.4, 0, 0, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.5, 0.4, 0.00, 0])
    sim_env.pb_ompl_interface.set_planner("RRTConnect")

    # # workpiece:C_continue
    # sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
    #                                     [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
    #                                     childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))
    # workpiece:dada
    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.02, -0.06 + 0.0125, 0.05 - 0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))

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
                time.sleep(1 / 240.)

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    sim_env.running = False
    cam_dist = 0.08
    pos, ori = sim_env.rm_sys.get_point_in_workpiece2robot((0.02 + cam_dist, -0.06 + 0.0125, 0.05 - 0.0125),
                                                           (0, 0.7071068, 0, -0.7071068))
    sim_env.calibration_pather.set_center(pos, ori)
    paths = sim_env.calibration_pather.generate_calibration_points(0.02, 8,start=[3.4,0,0,0,0,0])
    real_paths = {}
    for i, path in enumerate(paths.values()):
        total_time = 10 if i==0 else 1
        sampled_path = sim_env.interpolate_joint_path(path, 0.008, total_time)
        real_paths[f"point_{i}"] = sampled_path


    ori_path = paths[0]
    sampled_path = sim_env.interpolate_joint_path(ori_path, 1/240.,10)

    # np.savez("test_data/interpolate_path_005.npz", **real_paths)
    # print('save success')
    sim_env.camera_open=False
    sim_env.running = True
    for i, path in enumerate(paths.values()):
        sim_env.pb_ompl_interface.execute(path, dynamics=True)
        sim_env.camera_open = True
        time.sleep(1)
        sim_env.camera_open = False
    sim_env.pb_ompl_interface.execute(ori_path, dynamics=True)
    sim_env.robot_list[0].set_joints_states(ori_path[0])
    time.sleep(1)
    sim_env.pb_ompl_interface.execute(sampled_path,dynamics=True)

    pass

def debug_cailbration():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()


    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 1, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.5, 0.4, -0.2, 0])
    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))
    calibration_pather = CalibrationPather(sim_env.robot_list[0], sim_env.pb_ompl_interface)

    sim_env.running = True
    cam_dist = 0.08
    pos, ori = sim_env.rm_sys.get_point_in_workpiece2robot((0.0325 + cam_dist, -0.072 + 0.0125, 0.05266 - 0.0125),
                                                           (0, 0.7071068, 0, -0.7071068))

    calibration_pather.set_center(pos, ori)
    paths = calibration_pather.generate_calibration_points(0.01,10)



    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            sim_env.camera.show_link_sys(3, -1, 1, name="camera")
            if sim_env.camera_open==True:
                sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    calibration_data = {}
    calibration_data["camera_matrix"] = sim_env.rm_sys.RGB_camera.get_pybullet_camera_K()
    point_data = {}
    for id,(T,path) in enumerate(zip(calibration_pather.T_nine_points.values(),paths.values())):
        print('采样第', id, '点')
        data = {}
        sim_env.pb_ompl_interface.execute(path, dynamics=True)
        sim_env.camera_open = True
        time.sleep(5)
        rgb_img = sim_env.rm_sys.RGB_camera.RGB_img
        data['img'] = rgb_img
        joint = sim_env.robot_list[0].get_joints_states()
        pos, ori = sim_env.robot_list[0].get_pos_ori_from_ik(joint, tcp_name=None)
        T_nine_point = sim_env.robot_list[0].pos_to_matrix(pos, ori)
        data["TB2E"] = T_nine_point
        point_data[f'point_{id}'] = data
        sim_env.camera_open = False
    calibration_data['point_data'] = point_data
    print("采样完成")
    np.savez("test_data/calibration_data.npz", **calibration_data)
    print("数据保存完成")

    # --------------------------------------------
    sim_env.robot_list[0].set_joints_states(paths[0][0])

    pos, ori = sim_env.rm_sys.get_point_in_workpiece2world([0.05, -0.08, 0.14], p.getQuaternionFromEuler([0, 0, PI / 2]))
    sim_env.board.reset_position_and_orientation(position=pos,
                                              orientation=ori)

    path = paths[0]
    sim_env.pb_ompl_interface.execute(path, dynamics=True)
    calibration_data = {}
    calibration_data["camera_matrix"] = sim_env.rm_sys.RGB_camera.get_pybullet_camera_K()
    point_data = {}
    data = {}
    sim_env.camera_open = True
    time.sleep(5)
    rgb_img = sim_env.rm_sys.RGB_camera.RGB_img
    data['img'] = rgb_img
    joint = sim_env.robot_list[0].get_joints_states()
    pos, ori = sim_env.robot_list[0].get_pos_ori_from_ik(joint, tcp_name=None)
    T_nine_point = sim_env.robot_list[0].pos_to_matrix(pos, ori)
    data["TB2E"] = T_nine_point
    point_data[f'point_{0}'] = data
    sim_env.camera_open = False
    calibration_data['point_data'] = point_data
    print("偏差点采样完成")
    np.savez("test_data/calibration_data_for_update.npz", **calibration_data)
    print("数据保存完成")



def debug_board():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board, [0.0325, -0.072+0.0125, 0.05266-0.0125],
                                        childOrientation=p.getQuaternionFromEuler([0, 0, PI/2]))

    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 0, name="workpiece_mass")
            sim_env.board.show_link_sys(-1,-1,1,name="board")
            sim_env.board.show_link_sys(0, -1, 1, name="board1")
            sim_env.board.show_link_sys(1, -1, 1, name="board2")
            if sim_env.camera_open == True:
                sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

def debug_cam():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,[0.05, 0, 0.0125],childOrientation=p.getQuaternionFromEuler([0, 0, PI/2]))


    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 0, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]

    target_point_in_robot_sys1 = sim_env.rm_sys.get_point_in_workpiece2robot((0.12, -0.0, 0.1),
                                                                            (0,0.707,0,-0.707))

    target_point_in_robot_sys2 = sim_env.rm_sys.get_point_in_workpiece2robot((0,-0.0,0.08),(0.0005629,0.706825,0.707388,0.0005633))
    # target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((0,-0.3,0.5),(0,0,0, 1))
    joints = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys1[0], target_point_in_robot_sys1[1],
                                                     start=None, maxNumIteration=10000, tcp_name="RGB_camera")
    goal1 = joints

    joints = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys2[0], target_point_in_robot_sys2[1],
                                                     start=None, maxNumIteration=10000, tcp_name="rolling_tool")
    goal2 = joints
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.rm_sys.init_machine(sim_env.machine,'pos',[0.0, -0.0, 0.5, 0.4, -0.02,0])

    # sim_env.robot_list[0].set_joints_states(goal1)
    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal1)


    for _ in range(100):
        sim_env.step_simulation()
        # time.sleep(sim_env.time_step)
    time.sleep(2)

    # 执行规划
    sim_env.pb_ompl_interface.z_range = (0.01, 0.2)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.01, 0.01)
    sim_env.pb_ompl_interface.y_range = (-0.02, 0.02)
    sim_env.pb_ompl_interface.yaw_range = 10
    sim_env.pb_ompl_interface.roll_range = 5
    sim_env.pb_ompl_interface.pitch_range = 5


    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # sim_env.pb_ompl_interface.set_state_sampler(taskspaceRRT.MixedValidStateSampler(sim_env.pb_ompl_interface.si, sim_env.pb_ompl_interface.sample_in_task_space, ratio=0.8))
    res1, path1 = sim_env.pb_ompl_interface.plan_start_goal(start,goal1)

    sim_env.pb_ompl_interface.get_T_goal(goal, tcp_name="rolling_tool")
    sim_env.pb_ompl_interface.set_tsRRT_sample()
    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # sim_env.pb_ompl_interface.set_state_sampler(taskspaceRRT.MixedValidStateSampler(sim_env.pb_ompl_interface.si, sim_env.pb_ompl_interface.sample_in_task_space, ratio=0.8))
    res2, path2 = sim_env.pb_ompl_interface.plan_start_goal(goal1,goal2)




    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            sim_env.camera.show_link_sys(3, -1, 1, name="camera")
            if sim_env.camera_open==True:
                sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()
    if res1:
        sim_env.pb_ompl_interface.execute(path1, dynamics=True)
    sim_env.camera_open = True
    time.sleep(10)
    sim_env.camera_open = False
    if res2:
        sim_env.pb_ompl_interface.execute(path2, dynamics=True)


if __name__ == '__main__':
    # debug_cailbration()
    # debug_board()
    # debug_full_cailbration()
    debug_interpolate_joint_path()
    # debug_cam()