import numpy as np
import pylab as p

from agent_project.simulation.environment import *
from agent_project.simulation.calibrator import *

class DebugEnvironment(SimulationEnvironment):
    def __init__(self):
        super().__init__()

    def load_scene(self):
        # self.base_path = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/execution/simulation"
        workpiece_urdf = r"./models/6061_C_continue/urdf/6061_C_continue.urdf"
        # workpiece_urdf = r"./models/work_piece_dada/urdf/work_piece_dada.urdf"
        workpiece_urdf = os.path.join(self.base_path, workpiece_urdf)

        machine_file_name = r"./models/c501-simple.SLDASM/urdf/c501-simple.SLDASM.urdf"
        machine_file_name = os.path.join(self.base_path, machine_file_name)
        robot_urdf = r"./models/jaka_description/urdf/jaka_minicobo.urdf"
        robot_urdf = os.path.join(self.base_path, robot_urdf)
        robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool_12mm.urdf"
        robot_with_rolling_tool_urdf = os.path.join(self.base_path, robot_with_rolling_tool_urdf)
        machine = Machine(self.physics_client)
        self.machine = machine
        self.machine.load_urdf(fileName=machine_file_name, basePosition=(0, 0, 0), useFixedBase=1, flags=0, )
        self.object_list.append(self.machine.id_robot)
        self.workpiece_pose = [0.0, 0.06, 0.04]
        orientation = [0.0, 0.0, 0.0]
        quaternion = p.getQuaternionFromEuler(orientation, physicsClientId=self.physics_client)
        self.workpiece_orientation = quaternion
        self.workpiece_id = self.machine.add_workpiece_to_machine(workpiece_urdf, position=self.workpiece_pose,
                                                                  orientation=orientation)

        # self.object_list.append(self.workpiece_id)
        robot_id = self.load_robot(urdf_path=robot_with_rolling_tool_urdf, basePosition=(-0.16, -0.15, 0.7), baseOrientation=(0.7,0,0,0.7),useFixedBase=0,
                            start=[0, 0, PI / 2, 0, 0, 0], )
        # 消除执行器于机械臂末端的碰撞
        p.setCollisionFilterPair(robot_id, robot_id, 5, 7, 0, physicsClientId=self.physics_client)
        p.setCollisionFilterPair(robot_id, robot_id, 5, 8, 0, physicsClientId=self.physics_client)
        p.setCollisionFilterPair(robot_id, robot_id, 4, 8, 0, physicsClientId=self.physics_client)

        # 设置机械臂-rolling_tools的tcp坐标
        ee_pos, ee_orn = p.getLinkState(robot_id, 6, physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 10, physicsClientId=self.physics_client)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool", tcp_in_ee_matrix)
        ee_pos, ee_orn = p.getLinkState(robot_id, 6, physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 7, physicsClientId=self.physics_client)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool_base", tcp_in_ee_matrix)

        self.robot_list[0].inverse_mode = "body_sys"

        # 加载物理相机
        cam_urdf = "./models/camera/urdf/camera.urdf"
        cam_urdf = os.path.join(self.base_path, cam_urdf)
        self.camera = Robot(self.physics_client)
        self.camera.load_urdf(fileName=cam_urdf, basePosition=(0.05, -0.10, 0.75),
                              baseOrientation=p.getQuaternionFromEuler([PI/2, 0, 0]), useFixedBase=0)

        # 配置系统
        self.rm_sys = RM_sys(self.robot_list, self.physics_client)

        # 绑定机床到机械臂
        self.rm_sys.init_machine(self.machine, type='velocity')
        self.rm_sys.create_constrain(self.machine, self.robot_list[0], parentPosition=[-0.2, +0.1, 0.08],
                                     childOrientation=[0.7068252, 0, 0, 0.7073883]
                                     , workpiece_pos=self.workpiece_pose, workpiece_ori=self.workpiece_orientation)
        self.rm_sys.init_robot(self.robot_list[0])

        # 加载标定板
        board_urdf = "./models/calibration_board/urdf/calibration_board.urdf"
        board_urdf = os.path.join(self.base_path, board_urdf)
        self.board = Calibration_board(self.physics_client, board_urdf)
        self.rm_sys.robot_list.append(self.board)
        self.rm_sys.robot_list.append(self.machine.workpiece)
        pos, ori = self.rm_sys.get_point_in_workpiece2world([0.05, -0.05, 0.12],
                                                            p.getQuaternionFromEuler([0, 0, PI / 2],
                                                                                     physicsClientId=self.physics_client))
        self.board.reset_position_and_orientation(position=pos,
                                                  orientation=ori)

        # 绑定相机到机械臂
        self.rm_sys.camera = self.camera
        self.robot_list[0].id_end_effector = 7
        self.camera_constraint = self.rm_sys.bind_cam2robot(self.robot_list[0], self.camera,
                                                            pos_in_robot_end_link=[0, -0.05, -0.00358],
                                                            pos_in_cam_base_link=[0, 0, 0],
                                                            ori_in_cam_base_link=[-1.57, 0, 3.14])
        self.rm_sys.create_virtual_cams(60)
        # 设置机械臂-物理相机的tcp坐标
        for _ in range(100):
            self.step_simulation()
        ee_pos, ee_orn = p.getLinkState(robot_id, 6, physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(self.camera.id_robot, 3, physicsClientId=self.physics_client)[4:6]  # RGB_Link
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("RGB_camera", tcp_in_ee_matrix)

        # setup pb_ompl
        self.obstacles = []
        # self.pb_ompl_interface = pb_ompl.PbOMPL(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface = taskspaceRRT.TaskSpaceRRT(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface.set_planner("RRT")
        self.obstacles.extend([self.workpiece_id, self.machine.id_robot])
        self.pb_ompl_interface.set_obstacles(self.obstacles)
        # 消除ompl规划时link4与link8的碰撞
        self.pb_ompl_interface.check_link_pairs.remove((4, 8))
        self.pb_ompl_interface.check_link_pairs.remove((4, 9))

        # 设置九点标定
        self.calibration_pather = CalibrationPather(self.robot_list[0], self.pb_ompl_interface)
        self.calibrator: HandEyeCalibrator | None = None

        pass




def debug_interpolate_joint_path():
    import time
    sim_env = DebugEnvironment()
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
    sim_env.rm_sys.init_machine(sim_env.machine, 'pos', [0.0, -0.0, 0.4, 0, 0.005, 0])
    # sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # # workpiece:C_continue
    # sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
    #                                     [0.0325, -0.072 + 0.0125, 0.05266 - 0.0125],
    #                                     childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))
    # # workpiece:dada
    # sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
    #                                     [0.02, -0.06 + 0.0125, 0.05 - 0.0125],
    #                                     childOrientation=p.getQuaternionFromEuler([0, 0, PI / 2]))

    # 标定板朝向世界坐标系的z轴正方向
    sim_env.rm_sys.bind_board2workpiece(sim_env.machine.workpiece, sim_env.board,
                                        [0.03 + 0.148, -0.072 + 0.0125, 0.04 + 0.0025],
                                        childOrientation=p.getQuaternionFromEuler([-PI / 2, 0, PI/2]))

    # 这里标定板坐标系有问题，需要旋转Z轴才能和标定数据对齐


    calibration_data = np.load('/home/lwh/Project/python_project/Ai_agent/agent_project_v2/execution/physical/data/calibration_data.npz',allow_pickle=True)
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
    file_path = r'/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压到位点_6061_C轴连续加工.cls'
    time.sleep(2)


    sim_env.update_workpiece2robotBy_calibration()
    sim_env.update_robot_constrain()
    sim_env.update_camera_constrain()
    sim_env.running = False
    cam_dist = 0.0

    goto, origin_data = sim_env.rm_sys.read_cls_file(sim_env.robot_list[0], file_path, inverse=True)
    pos_list, ori_list = [], []
    for item in goto:
        # 解包位置信息pos (X/Y/Z)
        pos_list.append((item['X'], item['Y'], item['Z']))
        # 解包姿态信息ori (x/y/z/w)
        ori_list.append((item['O']['x'], item['O']['y'], item['O']['z'], item['O']['w']))

    pos, ori = pos_list[1789], ori_list[1789]
    start = [0.009722571130301054,
 -0.016613254465259873,
 -0.9593426914730804,
 0.0195544112008826,
 -1.9986100639060052,
 -0.8151708154450609]
    goal = sim_env.robot_list[0].get_state_from_ik(pos,ori,start=start,tcp_name='rolling_tool')
    print("after:pos:", pos, "ori:", ori)

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
