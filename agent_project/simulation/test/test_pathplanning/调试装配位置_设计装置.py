
from math import pi as PI
import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# from agent_project.simulation.calibrator import *
from agent_project.simulation.Robot import Robot
from agent_project.simulation.Machine import Machine
from agent_project.simulation.RM_sys import RM_sys
from agent_project.simulation import pb_ompl,taskspaceRRT
import pybullet as p
import pybullet_data
import time
import numpy as np
PI = np.pi
from scipy.interpolate import CubicSpline
from agent_project.simulation.pb_ompl import DEFAULT_PLANNING_TIME
DEFAULT_PLANNING_TIME = 20.0
from agent_project.simulation.test.goals_utils import expand_goal_states_nearby
for k in ["QT_PLUGIN_PATH","QT_QPA_PLATFORM_PLUGIN_PATH","LD_LIBRARY_PATH","PYTHONPATH"]:
    print(k, "=", os.environ.get(k))

# 2) 清掉 PyCharm/环境注入的“cv2 自带插件路径” 这样做是因为调试时 PyBullet GUI 会报错找不到 Qt 插件
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_PLUGIN_PATH", None)

class SimulationEnvironment:
    def __init__(self):
        self.physics_client = None
        self.running = False
        self.time_step = 1 / 240  # 仿真步进时间
        self.robot_id = None
        self.robot_list : list[pb_ompl.PbOMPLRobot|Robot] = []
        self.object_list = []
        self.camera_open = False
        self.base_path = os.path.dirname(os.path.abspath(__file__))



    def clear_env(self):
        """ 清空仿真环境 """
        for object_id in self.object_list:
            p.removeBody(object_id)

    def initialize(self):
        """ 初始化仿真环境 """
        # 重置仿真环境
        if self.physics_client is not None:
            p.disconnect()
        self.physics_client = p.connect(p.GUI)  # GUI 模式
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1,
                                   physicsClientId=self.physics_client)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI,0, physicsClientId=self.physics_client) # 关闭GUI信息展示
        p.addUserDebugLine([0, 0, 0], [1, 0, 0], lineColorRGB=[1, 0, 0], lineWidth=2)
        p.addUserDebugLine([0, 0, 0], [0, 1, 0], lineColorRGB=[0, 1, 0], lineWidth=2)
        p.addUserDebugLine([0, 0, 0], [0, 0, 1], lineColorRGB=[0, 0, 1], lineWidth=2)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        # p.setGravity(0, 0, -9.81)
        self.running = True
        print("Simulation environment initialized")


    def load_scene(self):

        workpiece_urdf = r"./models/6061_C_continue/urdf/6061_C_continue.urdf"
        # workpiece_urdf = r"./models/work_piece_dada/urdf/work_piece_dada.urdf"
        workpiece_urdf = os.path.join(self.base_path, workpiece_urdf)
        machine_file_name = r"./models/c501-simple.SLDASM/urdf/c501-simple.SLDASM.urdf"
        machine_file_name = os.path.join(self.base_path, machine_file_name)
        robot_urdf = r"./models/jaka_description/urdf/jaka_minicobo.urdf"
        robot_urdf = os.path.join(self.base_path, robot_urdf)
        robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool_12mm_len248dot37mm.urdf"
        robot_with_rolling_tool_urdf = os.path.join(self.base_path, robot_with_rolling_tool_urdf)
        machine = Machine(self.physics_client)
        self.machine = machine
        machine.load_urdf(fileName=machine_file_name, basePosition=(0, 0, 0), useFixedBase=1, flags=0, )
        self.object_list.append(self.machine.id_robot)
        self.workpiece_pose = [0.0, 0.15, 0.04]
        orientation = [0.0, 0.0, 0.0]
        quaternion = p.getQuaternionFromEuler(orientation)
        self.workpiece_orientation = quaternion
        self.workpiece_id = machine.add_workpiece_to_machine(workpiece_urdf, position=self.workpiece_pose,
                                                             orientation=orientation)

        # self.object_list.append(self.workpiece_id)
        robot_id = self.load_robot(urdf_path=robot_with_rolling_tool_urdf, basePosition=(-0.16, -0.15, 0.7), baseOrientation=(0.7,0,0,0.7),useFixedBase=0,
                            start=[0, 0, PI / 2, 0, 0, 0], )
        # 消除执行器于机械臂末端的碰撞
        p.setCollisionFilterPair(robot_id, robot_id, 5, 7, 0)
        p.setCollisionFilterPair(robot_id, robot_id, 5, 8, 0)
        p.setCollisionFilterPair(robot_id, robot_id, 4, 8, 0)

        # 设置机械臂-rolling_tools的tcp坐标
        ee_pos,ee_orn = p.getLinkState(robot_id, 6)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 10)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn,ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool",tcp_in_ee_matrix)
        ee_pos, ee_orn = p.getLinkState(robot_id, 6)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 7)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool_base", tcp_in_ee_matrix)

        self.robot_list[0].inverse_mode = "body_sys"

        # 加载物理相机
        # cam_urdf = "./models/camera/urdf/camera.urdf"
        # cam_urdf = os.path.join(self.base_path, cam_urdf)
        # self.camera = Robot(self.physics_client)
        # self.camera.load_urdf(fileName=cam_urdf, basePosition=(0.05, -0.10, 0.75),
        #                  baseOrientation=p.getQuaternionFromEuler([1.57, 0, 0]), useFixedBase=0)

        # 配置系统
        self.rm_sys = RM_sys(self.robot_list, self.physics_client)


        # 绑定机床到机械臂
        self.rm_sys.init_machine(machine, type='velocity')
        # 因为设计的装置太长了，需要把机械臂往后移动100mm
        self.rm_sys.create_constrain(machine,self.robot_list[0],parentPosition=[-0.18, +0.1 -0.1, 0.12], childOrientation=[0.7068252, 0, 0, 0.7073883]
                                     ,workpiece_pos=self.workpiece_pose,workpiece_ori=self.workpiece_orientation)
        self.rm_sys.init_robot(self.robot_list[0])

        # 加载标定板
        # board_urdf = "./models/calibration_board/urdf/calibration_board.urdf"
        # board_urdf = os.path.join(self.base_path, board_urdf)
        # self.board = Calibration_board(self.physics_client,board_urdf)
        # self.rm_sys.robot_list.append(self.board)
        # self.rm_sys.robot_list.append(self.machine.workpiece)
        # pos, ori = self.rm_sys.get_point_in_workpiece2world([0.05, -0.05, 0.12],
        #                                                     p.getQuaternionFromEuler([0, 0, PI/2]))
        # self.board.reset_position_and_orientation(position=pos,
        #                                           orientation=ori)

        # 绑定相机到机械臂
        # self.rm_sys.camera = self.camera
        # self.robot_list[0].id_end_effector = 7
        # self.camera_constraint = self.rm_sys.bind_cam2robot(self.robot_list[0], self.camera,
        #                                                     pos_in_robot_end_link=[0, -0.05, -0.00358],
        #                                                     pos_in_cam_base_link=[0, 0, 0],
        #                                                     ori_in_cam_base_link=[-1.57, 0, 3.14])
        # self.rm_sys.create_virtual_cams(60)
        # 设置机械臂-物理相机的tcp坐标
        # for _ in range(100):
        #     self.step_simulation()
        # ee_pos, ee_orn = p.getLinkState(robot_id, 6)[4:6]
        # tcp_pos, tcp_orn = p.getLinkState(self.camera.id_robot, 3)[4:6]  # RGB_Link
        # tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        # self.robot_list[0].add_tcp("RGB_camera", tcp_in_ee_matrix)



        # setup pb_ompl
        self.obstacles = []
        # self.pb_ompl_interface = pb_ompl.PbOMPL(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface = taskspaceRRT.TaskSpaceRRT(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface.set_planner("RRT")
        self.obstacles.extend([self.workpiece_id,machine.id_robot])
        self.pb_ompl_interface.set_obstacles(self.obstacles)
        # 消除ompl规划时link4与link8的碰撞
        self.pb_ompl_interface.check_link_pairs.remove((4,8))
        self.pb_ompl_interface.check_link_pairs.remove((4, 9))

        # 设置九点标定
        # self.calibration_pather = CalibrationPather(self.robot_list[0], self.pb_ompl_interface)
        # self.calibrator : HandEyeCalibrator|None = None

        pass

    def step_simulation(self):
        """ 进行仿真步进 """
        p.stepSimulation()

    def clear_obstacles(self):
        for obstacle in self.obstacles:
            p.removeBody(obstacle)

    def add_object(self, urdf_path,  basePosition,baseOrientation,useFixedBase):
        """ 向仿真环境添加物体 """
        if basePosition is None:
            basePosition = [0, 0, 0]
        if baseOrientation is None:
            baseOrientation = [0, 0, 0, 1]
        obj_id = p.loadURDF(urdf_path, basePosition=basePosition, baseOrientation=baseOrientation,useFixedBase=useFixedBase)
        self.obstacles.append(obj_id)
        return obj_id

    def load_robot(self, urdf_path, basePosition,baseOrientation,useFixedBase,start=None):
        """ 加载机械臂 """
        if basePosition is None:
            basePosition = [0, 0, 0]
        if baseOrientation is None:
            baseOrientation = [0, 0, 0, 1]

        robot = pb_ompl.PbOMPLRobot(self.physics_client)
        robot.f_print = True
        robot.load_urdf(fileName=urdf_path, basePosition=basePosition,baseOrientation=baseOrientation, useFixedBase=useFixedBase,
                             flags=p.URDF_USE_SELF_COLLISION,
                             )
        if start is not None:
            robot.set_joints_states(start)
        else:
            robot.set_joints_states([0]*robot.num_avail_joints)

        self.robot_list.append(robot)
        self.object_list.append(robot.id_robot)
        return robot.id_robot

    def get_robot_end_pos_and_ori(self, robot_id):
        """ 获取机械臂末端位置 """
        if robot_id is None:
            return "No robot loaded"

        robot = [robot for robot in self.robot_list if robot.id_robot == robot_id][0]

        end_pos, end_orn = robot.get_end_effector_info()
        return end_pos,end_orn


    def move_robot_to_target(self, robot_id, target_position, target_orientation=None,maxVelocity=10):
        """ 控制机械臂移动到目标位置 """
        if robot_id is None:
            return "No robot loaded"
        robot = [robot for robot in self.robot_list if robot.id_robot == robot_id][0]
        lower_limits = [info[1] for info in [robot.info_joints[j] for j in robot.ids_avail_joints]]
        upper_limits = [info[2] for info in [robot.info_joints[j] for j in robot.ids_avail_joints]]
        joint_ranges = [v1 - v2 for v1, v2 in zip(upper_limits, lower_limits)]

        try:
            joint_positions = p.calculateInverseKinematics(robot.id_robot, robot.id_end_effector,
                                                            targetPosition=target_position,
                                                            targetOrientation=target_orientation,
                                                            upperLimits=upper_limits, lowerLimits=lower_limits,
                                                            jointRanges=joint_ranges,
                                                            maxNumIterations=100,
                                                            # currentPositions=currentPosition,
                                                            )
        except Exception as e:
            print(e)
            return "IK failed"

        try:
            for i in range(min(len(joint_positions), robot.num_avail_joints)):
                p.setJointMotorControl2(
                    robot.id_robot, robot.ids_avail_joints[i], p.POSITION_CONTROL,maxVelocity=maxVelocity, targetPosition=joint_positions[i]
                )
        except Exception as e:
            print(e)
            return "Robot moved failed"

        return "Robot moved successfully"




    def move_robot(self, robot_id,joint_positions):
        """ 控制机械臂的关节 """
        if robot_id is None:
            return "No robot loaded"

        robot = [robot for robot in self.robot_list if robot.id_robot == robot_id][0]
        for i in range(min(len(joint_positions), robot.num_avail_joints)):
            p.setJointMotorControl2(
                robot_id, robot.ids_avail_joints[i],
                p.POSITION_CONTROL, targetPosition=joint_positions[i],force=1000,
                targetVelocity=0, maxVelocity=2,
                positionGain=0.4, velocityGain=0.8,
            )
        return "Robot moved successfully"
    def set_robot(self, robot_id,joint_positions):
        """ 控制机械臂的关节 """
        if robot_id is None:
            return "No robot loaded"

        robot = [robot for robot in self.robot_list if robot.id_robot == robot_id][0]
        for i in range(min(len(joint_positions), robot.num_avail_joints)):
            p.resetJointState(
                robot_id, robot.ids_avail_joints[i], targetValue=joint_positions[i]
            )
        return "Robot moved successfully"

    def create_cube(self,position,orientation, half_extents=[0.1,0.1,0.1], mass=1.0, color=[1, 0, 0, 1]):
        """
        在 PyBullet 中创建一个立方体

        :param position: 立方体的位置，格式为 [x, y, z]
        :param orientation: 立方体的朝向，格式为 [x, y, z, w]
        :param half_extents: 立方体的半边长，格式为 [x, y, z]
        :param mass: 立方体的质量，默认为 1.0, 0表示为固定物体
        :param color: 立方体的颜色，格式为 [r, g, b, a]，默认为红色不透明
        :return: 立方体的物体 ID
        """
        # 初始化 PyBullet 连接


        # 创建碰撞形状
        collision_shape = p.createCollisionShape(
            shapeType=p.GEOM_BOX,
            halfExtents=half_extents
        )

        # 创建视觉形状
        visual_shape = p.createVisualShape(
            shapeType=p.GEOM_BOX,
            halfExtents=half_extents,
            rgbaColor=color
        )

        # 创建多体对象（立方体）
        cube_id = p.createMultiBody(
            baseMass=mass,
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=visual_shape,
            basePosition=position,
            baseOrientation=orientation,
        )
        self.object_list.append(cube_id)

        return cube_id

    def get_object_pos_and_ori(self,object_id):
        """
        获取给定 ID 物体的位置

        :param object_id: 物体的 ID
        :return: 物体的位置，格式为 [x, y, z]
        """
        position, ori = p.getBasePositionAndOrientation(object_id)
        return position,ori

    def ninePoints_sample(self,center_joints):
        # 进行采样
        pos, ori = self.robot_list[0].get_pos_ori_from_ik(center_joints, tcp_name="RGB_camera")
        self.calibration_pather.set_center(pos, ori)
        paths = self.calibration_pather.generate_calibration_points(0.01, 10)
        calibration_data = {}
        calibration_data["camera_matrix"] = self.rm_sys.RGB_camera.get_pybullet_camera_K()
        point_data = {}
        for id, (T, path) in enumerate(zip(self.calibration_pather.T_nine_points.values(), paths.values())):
            print('采样第', id, '点')
            data = {}
            self.pb_ompl_interface.execute(path, dynamics=True)
            self.camera_open = True
            time.sleep(5)
            rgb_img = self.rm_sys.RGB_camera.RGB_img
            data['img'] = rgb_img
            joint = self.robot_list[0].get_joints_states()
            pos, ori = self.robot_list[0].get_pos_ori_from_ik(joint, tcp_name=None)
            T_nine_point = self.robot_list[0].pos_to_matrix(pos, ori)
            data["TB2E"] = T_nine_point
            point_data[f'point_{id}'] = data
            self.camera_open = False
        calibration_data['point_data'] = point_data
        print("采样完成")
        data_path = "./datas/calibration_datas/calibration_data.npz"
        data_path = os.path.join(self.base_path, data_path)
        np.savez(data_path, **calibration_data)
        print("数据保存完成:", data_path)


    def update_workpiece2robotBy_calibration(self):
        """
        更新工件坐标系到机械臂坐标系的变换矩阵
        :return:
        """
        if self.calibrator is None:
            print("请先进行标定")
            return
        T = self.calibrator.get_target2base()
        if self.rm_sys.T_board2workpiece is None:
            print("请先进行标定")
            return
        T_workpiece2robot = T @ np.linalg.inv(self.rm_sys.T_board2workpiece)
        board_pos, board_ori = self.board.show_link_sys(0, 1, 1)
        robotbase_pos, robotbase_ori = self.robot_list[0].show_link_sys(-1, 1, 1)
        tar2base = Robot.TAB_with_AinW_and_BinW(board_pos, board_ori, robotbase_pos, robotbase_ori)

        self.rm_sys.T_workpiece2robot = T_workpiece2robot.copy()
        return T_workpiece2robot

    def modify_workpiece_constrain(self,pos=None,ori=None):
        if pos is None:
            pos = self.workpiece_pose
        if ori is None:
            ori = self.workpiece_orientation

        if self.machine.workpiece_constrain:
            p.removeConstraint(self.machine.workpiece_constrain, self.physics_client)
            self.machine.workpiece_constrain = None

            # 更新工件参数
            self.workpiece_pose = pos
            self.workpiece_orientation = ori
            self.machine.workpiece_pose = pos
            self.machine.workpiece_orientation = ori

            # 重新创建约束
            self.machine.workpiece_constrain = self.rm_sys.createConstraintBase(self.machine.id_robot, self.machine.turntable_index,self.machine.workpiece.id_robot,-1,
                                             parentFramePosition=pos,
                                             childFramePosition=[0,0,0],
                                                childFrameOrientation=ori,
                                             physicsClientId=self.physics_client,
                                             )
        pass

    def update_robot_constrain(self):
        if self.rm_sys.robot_constrain:
            p.removeConstraint(self.rm_sys.robot_constrain,self.physics_client)
            self.rm_sys.robot_constrain = None
            # 获取工件坐标系在机床坐标系下的变换矩阵
            T_workpiece2machine = Robot.pos_to_matrix(self.workpiece_pose, self.workpiece_orientation)
            # 获取机械臂基座在机床坐标系下的变换矩阵
            T_robot2machine = T_workpiece2machine @ np.linalg.inv(self.rm_sys.T_workpiece2robot)
            robotbase_pos, robotbase_ori = Robot.matrix_to_pos(T_robot2machine)
            # 重新创建约束
            self.rm_sys.robot_constrain = self.rm_sys.create_constrain(self.machine, self.robot_list[0],
                                                                        parentPosition=robotbase_pos,
                                                                        childOrientation=robotbase_ori,
                                                                        workpiece_pos=self.workpiece_pose,
                                                                        workpiece_ori=self.workpiece_orientation)

        pass

    def update_camera_constrain(self):
        '''
        根据标定结果更新相机的位置
        :return:
        '''
        if self.camera_constraint:
            p.removeConstraint(self.camera_constraint, self.physics_client)
            self.camera_constraint = None
            T = self.robot_list[0].tcp_list['RGB_camera']
            pos_in_robot_end_link, _ = Robot.matrix_to_pos(T)
            _,ori_in_cam_base_link = Robot.matrix_to_pos(np.linalg.inv(T))  # 这里需要求父link相对于子link的姿态 于create constrain函数性质相关

            # pos_in_robot_end_link = [0,0,0]
            # ori_in_cam_base_link = [0,0,0,1]
            robot = self.robot_list[0]
            camera = self.camera
            robot_end_mass = Robot.get_com_in_link_frame(robot.id_robot, 5)
            robot_end_in_mass_sys = np.array(pos_in_robot_end_link) - np.array(robot_end_mass)

            camera_mass = Robot.get_com_in_link_frame(camera.id_robot, 3,)
            camera_in_mass_sys = - np.array(camera_mass)

            constraint_id = p.createConstraint(parentBodyUniqueId=robot.id_robot,
                                               parentLinkIndex=5,
                                               childBodyUniqueId=camera.id_robot,
                                               childLinkIndex=3,  # 表示连接到工件的基础部分
                                               jointType=p.JOINT_FIXED,  # p.JOINT_POINT2POINT p.JOINT_REVOLUTE
                                               jointAxis=[0, 0, 0],
                                               parentFramePosition=robot_end_in_mass_sys,
                                               childFramePosition=camera_in_mass_sys,
                                               childFrameOrientation=ori_in_cam_base_link,
                                               )

            p.changeConstraint(constraint_id, maxForce=1e6, )
            # # p.changeConstraint(constraint_id,  erp=0.2)
            for i in range(camera.id_end_effector + 1):
                p.setCollisionFilterPair(camera.id_robot, robot.id_robot, i, robot.id_end_effector,
                                         0,
                                         physicsClientId=self.physics_client)
                p.changeDynamics(camera.id_robot, i, mass=0.00001)
            for i in range(robot.num_all_joints + 1):
                p.setCollisionFilterPair(camera.id_robot, robot.id_robot, -1, i,
                                         0,
                                         physicsClientId=self.physics_client)
            #
            p.setCollisionFilterPair(camera.id_robot, robot.id_robot, -1, robot.id_end_effector,
                                     0,
                                     physicsClientId=self.physics_client)
            #
            p.changeDynamics(camera.id_robot, -1, mass=0.001)
            self.camera_constraint = constraint_id
        pass

    def interpolate_joint_path(self,path, steptime, totaltime):
        """
        对关节空间路径进行三次样条插值并按时间采样。

        参数:
            path (np.ndarray): 形状为 (N, D) 的路径数组，N 为路径点数量，D 为关节维度。
            steptime (float): 采样的时间步长（单位：秒）。
            totaltime (float): 路径总时间（单位：秒）。

        返回:
            sampled_path (np.ndarray): 插值后按时间采样得到的路径点，形状为 (M, D)，M 为采样点数。
        """
        path = np.array(path)
        N, D = path.shape

        # 计算弧长参数（累积距离）
        arc_lengths = [0.0]
        for i in range(1, N):
            dist = np.linalg.norm(path[i] - path[i - 1])
            arc_lengths.append(arc_lengths[-1] + dist)
        arc_lengths = np.array(arc_lengths)

        # 创建每个关节维度的三次样条插值函数
        splines = [CubicSpline(arc_lengths, path[:, d]) for d in range(D)]

        # 根据时间采样
        num_samples = int(totaltime / steptime) + 1
        sample_arc_lengths = np.linspace(0, arc_lengths[-1], num_samples)

        # 对每个采样点进行插值
        sampled_path = np.stack([spline(sample_arc_lengths) for spline in splines], axis=-1)

        return sampled_path

scene_config={
    "machine_state_A": np.array([0.0, 0.0, 0.4, 0.1, -0.02]),
    "machine_state_B": np.array([0.0, -0.0, 0.4, 0.3, -0.01]),
    "machine_state_C": np.array([-0.5, -0.2, 0.325, 0.34, 0.00]),
    "machine_state_D": np.array([0.4, -0.7, 0.48, 0.35, 0.025]),
}

scene_config2={
    "machine_state_A": np.array([0.0, 0.0, 0.4, 0.1, -0.02]),
    "machine_state_B": np.array([0.0, -0.0, 0.4, 0.35, -0.01]),
    "machine_state_C": np.array([-0.5, -0.2, 0.3, 0.41, 0.05]),
    "machine_state_D": np.array([0.4, -0.7, 0.48, 0.35, 0.025]),
}

planners = ["RRTConnect", "PRM", "RRTstar",  "Ours"]









import numpy as np

import numpy as np

def sample_rect_grid_points(points,
                            center_idx=None,
                            width=0.10,
                            height=0.06,
                            nx=10,
                            ny=10,
                            use_pca=True,
                            auto_center=False,
                            ref_right=(1.0, 0.0, 0.0),
                            ref_up=(0.0, 0.0, 1.0),
                            strict_cell=False):
    """
    在点云主平面中定义一个矩形区域，并按 nx * ny 网格进行空间均匀采样。
    每个网格单元选 1 个点，最终返回顺序严格为：
        左 -> 右， 下 -> 上

    参数
    ----
    points : list[(x,y,z)]
        输入点云
    center_idx : int or None
        矩形中心参考点索引（auto_center=False 时生效）
    width : float
        矩形宽度（沿 axis_u）
    height : float
        矩形高度（沿 axis_v）
    nx : int
        宽度方向网格数
    ny : int
        高度方向网格数
    use_pca : bool
        是否使用 PCA 主方向建立局部平面
    auto_center : bool
        True：矩形中心取 ROI 几何中心
        False：矩形中心取 center_idx 对应点
    ref_right : tuple/list/np.ndarray
        用来固定 axis_u 正方向（“右”方向）的参考向量
    ref_up : tuple/list/np.ndarray
        用来固定 axis_v 正方向（“上”方向）的参考向量
    strict_cell : bool
        True：每个格子必须从格子内部取点，空格子就空着
        False：空格子允许从 ROI 剩余点中找最近点回填

    返回
    ----
    selected_idx : list[int]
        选中的原始点索引，顺序严格为 左->右，下->上
    grid_selected : list[list[int|None]]
        二维网格结果，grid_selected[iy][ix]
    info : dict
        调试信息
    """
    pts = np.asarray(points, dtype=float)
    n = len(pts)

    if n == 0:
        return [], [], {"reason": "输入点为空"}

    centroid = pts.mean(axis=0)

    # 先转成参考向量
    ref_right = np.asarray(ref_right, dtype=float)
    ref_up = np.asarray(ref_up, dtype=float)

    # 1) 建立局部坐标系
    if use_pca and n >= 3:
        X = pts - centroid
        _, _, vh = np.linalg.svd(X, full_matrices=False)

        c0 = vh[0].copy()
        c1 = vh[1].copy()

        # 比较两种分配方式：
        # 方案A: c0->左右(axis_u), c1->上下(axis_v)
        score_keep = abs(np.dot(c0, ref_right)) + abs(np.dot(c1, ref_up))

        # 方案B: c1->左右(axis_u), c0->上下(axis_v)
        score_swap = abs(np.dot(c1, ref_right)) + abs(np.dot(c0, ref_up))

        if score_keep >= score_swap:
            axis_u, axis_v = c0, c1
        else:
            axis_u, axis_v = c1, c0

    else:
        axis_u = np.array([1.0, 0.0, 0.0], dtype=float)
        axis_v = np.array([0.0, 1.0, 0.0], dtype=float)

    # 2) 固定正负方向，避免“左/右、上/下”翻转
    if np.linalg.norm(ref_right) > 0 and np.dot(axis_u, ref_right) < 0:
        axis_u = -axis_u

    if np.linalg.norm(ref_up) > 0 and np.dot(axis_v, ref_up) < 0:
        axis_v = -axis_v

    # 3) 法向
    axis_n = np.cross(axis_u, axis_v)
    if np.linalg.norm(axis_n) > 1e-12:
        axis_n = axis_n / np.linalg.norm(axis_n)

    # 3) 投影到局部二维坐标 (u, v)
    rel = pts - centroid
    u_all = rel @ axis_u
    v_all = rel @ axis_v

    # 4) 确定矩形中心
    if auto_center or center_idx is None:
        u0 = 0.5 * (u_all.min() + u_all.max())
        v0 = 0.5 * (v_all.min() + v_all.max())
        center_3d = centroid + u0 * axis_u + v0 * axis_v
    else:
        center_idx = int(np.clip(center_idx, 0, n - 1))
        c = pts[center_idx]
        c_rel = c - centroid
        u0 = c_rel @ axis_u
        v0 = c_rel @ axis_v
        center_3d = c

    # 5) 矩形 ROI
    u_min, u_max = u0 - width / 2.0, u0 + width / 2.0
    v_min, v_max = v0 - height / 2.0, v0 + height / 2.0

    roi_mask = (
        (u_all >= u_min) & (u_all <= u_max) &
        (v_all >= v_min) & (v_all <= v_max)
    )
    roi_idx = np.where(roi_mask)[0]

    if len(roi_idx) == 0:
        return [], [[None for _ in range(nx)] for _ in range(ny)], {
            "reason": "矩形区域内没有点",
            "center_3d": center_3d,
            "axis_u": axis_u,
            "axis_v": axis_v,
            "axis_n": axis_n,
            "roi_count": 0,
            "selected_count": 0,
        }

    roi_u = u_all[roi_idx]
    roi_v = v_all[roi_idx]

    cell_w = width / nx
    cell_h = height / ny

    # 6) 用二维网格保存结果，保证最终顺序
    grid_selected = [[None for _ in range(nx)] for _ in range(ny)]
    used_global_idx = set()
    empty_cells = []

    # 第一轮：每格优先从格子内部取 1 个
    for iy in range(ny):          # 下 -> 上
        for ix in range(nx):      # 左 -> 右
            cu = u_min + (ix + 0.5) * cell_w
            cv = v_min + (iy + 0.5) * cell_h

            cell_u_min = u_min + ix * cell_w
            cell_u_max = u_min + (ix + 1) * cell_w
            cell_v_min = v_min + iy * cell_h
            cell_v_max = v_min + (iy + 1) * cell_h

            if ix < nx - 1:
                mask_u = (roi_u >= cell_u_min) & (roi_u < cell_u_max)
            else:
                mask_u = (roi_u >= cell_u_min) & (roi_u <= cell_u_max)

            if iy < ny - 1:
                mask_v = (roi_v >= cell_v_min) & (roi_v < cell_v_max)
            else:
                mask_v = (roi_v >= cell_v_min) & (roi_v <= cell_v_max)

            in_cell = mask_u & mask_v
            local_ids = np.where(in_cell)[0]

            if len(local_ids) > 0:
                best_idx = None
                best_dist2 = None

                for lid in local_ids:
                    gidx = int(roi_idx[lid])
                    if gidx in used_global_idx:
                        continue

                    du = roi_u[lid] - cu
                    dv = roi_v[lid] - cv
                    dist2 = du * du + dv * dv

                    if (best_dist2 is None) or (dist2 < best_dist2):
                        best_dist2 = dist2
                        best_idx = gidx

                if best_idx is not None:
                    grid_selected[iy][ix] = best_idx
                    used_global_idx.add(best_idx)
                else:
                    empty_cells.append((iy, ix, cu, cv))
            else:
                empty_cells.append((iy, ix, cu, cv))

    # 第二轮：空格回填（可选）
    if not strict_cell:
        remaining = [int(g) for g in roi_idx if int(g) not in used_global_idx]

        for iy, ix, cu, cv in empty_cells:
            if not remaining:
                break

            rem = np.asarray(remaining, dtype=int)
            du = u_all[rem] - cu
            dv = v_all[rem] - cv
            dist2 = du * du + dv * dv
            best_pos = int(np.argmin(dist2))
            best_idx = int(rem[best_pos])

            grid_selected[iy][ix] = best_idx
            used_global_idx.add(best_idx)
            remaining.remove(best_idx)

    # 7) 按固定顺序展开：左->右，下->上
    selected_idx = [
        grid_selected[iy][ix]
        for iy in range(ny)  # 下 -> 上
        for ix in range(nx)  # 右 -> 左 # for ix in range(nx)  # 左 -> 右




        if grid_selected[iy][ix] is not None
    ]

    info = {
        "center_3d": center_3d,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "u_min": u_min,
        "u_max": u_max,
        "v_min": v_min,
        "v_max": v_max,
        "roi_count": int(len(roi_idx)),
        "selected_count": int(len(selected_idx)),
        "grid_shape": (nx, ny),
        "cell_w": cell_w,
        "cell_h": cell_h,
    }

    return selected_idx, grid_selected, info

def sample_indices_evenly(indices, sample_num=100):
    if len(indices) <= sample_num:
        return indices
    arr = np.linspace(0, len(indices) - 1, sample_num, dtype=int)
    return [indices[i] for i in arr]

def get_test_points():
    loaded_points = np.load("./path_files/highlight_points.npy", allow_pickle=True)
    highlight_points = loaded_points.tolist()
    return highlight_points
    pass
def highlight_points():
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    machine_state = scene_config["machine_state_A"]
    sim_env.machine.set_joints_states(machine_state)
    for _ in range(100):
        sim_env.step_simulation()

    file_path = r'/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压到位点_6061_C轴连续加工.cls'

    goto,origin_data = sim_env.rm_sys.read_cls_file(sim_env.robot_list[0], file_path, inverse=True)

    pos_list, ori_list = [], []
    for item in goto:
        # 解包位置信息pos (X/Y/Z)
        pos_list.append((item['X'], item['Y'], item['Z']))
        # 解包姿态信息ori (x/y/z/w)
        ori_list.append((item['O']['x'], item['O']['y'], item['O']['z'], item['O']['w']))

    coordinates = [item[0] for item in origin_data]
    selected_idx, grid_selected, rect_info = sample_rect_grid_points(
        coordinates,
        center_idx=None,
        width=0.10,
        height=0.15,
        nx=10,
        ny=10,
        use_pca=True,
        auto_center=True,
        ref_right=(-1.0, 0.0, 0.0),  # 全局 X 作为“右”
        ref_up=(0.0, 0.0, 1.0),  # 全局 Z 作为“上”
        strict_cell=False  # 允许空格回填，尽量凑满 100 个
    )
    # highlight_points = [(origin_data[i][0], origin_data[i][1]) for i in selected_idx]
    # save_path = "./path_files/highlight_points.npy"
    # np.save(save_path, np.array(highlight_points, dtype=object), allow_pickle=True)
    # print(f"Saved {len(highlight_points)} highlight points to {save_path}")

    highlight_positions = [origin_data[i][0] for i in selected_idx]


    highlight_positions_in_world = []
    sim_env.rm_sys.get_point_in_workpiece2world((0,0,0), (0, 0, 0, 1), workpiece=sim_env.machine.workpiece)
    for pos in highlight_positions:
        pos_in_world = sim_env.rm_sys.get_point_in_workpiece2world(pos,(0,0,0,1))
        highlight_positions_in_world.append(pos_in_world[0])
    # 高亮显示（红色点）
    p.addUserDebugPoints(
        pointPositions=highlight_positions_in_world,
        pointColorsRGB=[[1, 0, 0] for _ in highlight_positions],
        pointSize=5,
        lifeTime=0  # 0 表示常驻显示
    )
    # ================================

    start = [1.57, 0, -1, 0, 0, 0, ]


    target_points_in_robot_sys =  [(pos_list[i],ori_list[i]) for i in selected_idx]
    target_point_in_robot_sys = target_points_in_robot_sys[50]

    # target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((0,-0.3,0.5),(0,0,0, 1))
    joints = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys[0], target_point_in_robot_sys[1],
                                                     start=None, maxNumIteration=10000, tcp_name="rolling_tool")
    goal = joints
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)


    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal)
    sim_env.robot_list[0].set_joints_states(goal)

    start = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933, -1.8410220234890533, -0.6757545624540242]
    for _ in range(100):
        sim_env.step_simulation()
        joints = sim_env.robot_list[0].get_state_from_ik(target_points_in_robot_sys[_][0],
                                                                                        target_points_in_robot_sys[_][1],
                                                     start=start, maxNumIteration=10000, tcp_name="rolling_tool")
        sim_env.robot_list[0].set_joints_states(joints)
        print(f"Moving to point {_}, joints: {joints}")
        # collision
        safe = sim_env.pb_ompl_interface.is_state_valid(joints)
        if not safe:
            print(f"Collision detected at step {_} for joints: {joints}")
            time.sleep(1)

        time.sleep(0.1)
    time.sleep(2)

    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            # sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()


def test_point():

    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()


    point_in_workpiece = [0.01965,-0.05525,0.22536]
    ori_in_workpiece = [-0.1032456671688744, 0.6995286500286133, 0.6995286500286133, -0.1032456671688744]
    target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot(point_in_workpiece, ori_in_workpiece)

    start_eve = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933, -1.8410220234890533,
             -0.6757545624540242]

    goal = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys[0], target_point_in_robot_sys[1],
                                                   start=start_eve, maxNumIteration=10000, tcp_name="rolling_tool")
    print("goal",goal)
    path = np.load(
        "/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压_path.npy")

    start_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot([0.0,-0.090,0.040], [ 0, 0.7071068, 0.7071068, 0 ])
    start = sim_env.robot_list[0].get_state_from_ik(start_point_in_robot_sys[0], start_point_in_robot_sys[1],
                                                   start=start_eve,
                                                    maxNumIteration=10000, tcp_name="rolling_tool")
    print("start",start)
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    machine_state = scene_config["machine_state_A"]
    sim_env.machine.set_joints_states(machine_state)
    time.sleep(2)

    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal)
    sim_env.robot_list[0].set_joints_states(goal)

    for _ in range(100):
        sim_env.step_simulation()
        # time.sleep(sim_env.time_step)
    time.sleep(2)


    # 执行规划
    sim_env.pb_ompl_interface.get_T_goal(goal,tcp_name="rolling_tool")
    sim_env.pb_ompl_interface.z_range = (0.01, 0.15)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.005,0.005)
    sim_env.pb_ompl_interface.y_range = (-0.001,0.001)
    sim_env.pb_ompl_interface.yaw_range = 3
    sim_env.pb_ompl_interface.roll_range = 1
    sim_env.pb_ompl_interface.pitch_range = 1
    # sim_env.pb_ompl_interface.set_tsRRT_sample()
    # sim_env.pb_ompl_interface.space.state_sampler.ratio=0.3
    sim_env.pb_ompl_interface.set_random_sample()
    sim_env.pb_ompl_interface.set_planner("RRTConnect")

    start = sim_env.pb_ompl_interface.robot.get_cur_state()
    res, ori_path, path, solved_time, total_states = sim_env.pb_ompl_interface.plan_start_goal(start,goal,allowed_time=30,ret_all=True)


    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            # sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()
    if res:
        sim_env.pb_ompl_interface.execute(path, dynamics=True)

from tqdm import tqdm
def export_path():
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    machine_state = scene_config["machine_state_A"]
    sim_env.machine.set_joints_states(machine_state)
    for _ in range(100):
        sim_env.step_simulation()

    file_path = r'/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/6061_A_01mm.cls'

    goto, origin_data = sim_env.rm_sys.read_cls_file(sim_env.robot_list[0], file_path, inverse=True)

    pos_list, ori_list = [], []
    for item in goto:
        # 解包位置信息pos (X/Y/Z)
        pos_list.append((item['X'], item['Y'], item['Z']))
        # 解包姿态信息ori (x/y/z/w)
        ori_list.append((item['O']['x'], item['O']['y'], item['O']['z'], item['O']['w']))

    coordinates = [item[0] for item in origin_data]
    selected_idx, grid_selected, rect_info = sample_rect_grid_points(
        coordinates,
        center_idx=None,
        width=0.10,
        height=0.15,
        nx=10,
        ny=10,
        use_pca=True,
        auto_center=True,
        ref_right=(-1.0, 0.0, 0.0),  # 全局 X 作为“右”
        ref_up=(0.0, 0.0, 1.0),  # 全局 Z 作为“上”
        strict_cell=False  # 允许空格回填，尽量凑满 100 个
    )
    # highlight_points = [(origin_data[i][0], origin_data[i][1]) for i in selected_idx]
    # save_path = "./path_files/highlight_points.npy"
    # np.save(save_path, np.array(highlight_points, dtype=object), allow_pickle=True)
    # print(f"Saved {len(highlight_points)} highlight points to {save_path}")

    highlight_positions = [origin_data[i][0] for i in selected_idx]

    highlight_positions_in_world = []
    sim_env.rm_sys.get_point_in_workpiece2world((0, 0, 0), (0, 0, 0, 1), workpiece=sim_env.machine.workpiece)
    for pos in highlight_positions:
        pos_in_world = sim_env.rm_sys.get_point_in_workpiece2world(pos, (0, 0, 0, 1))
        highlight_positions_in_world.append(pos_in_world[0])
    # 高亮显示（红色点）
    p.addUserDebugPoints(
        pointPositions=highlight_positions_in_world,
        pointColorsRGB=[[1, 0, 0] for _ in highlight_positions],
        pointSize=5,
        lifeTime=0  # 0 表示常驻显示
    )
    # ================================

    start = [1.57, 0, -1, 0, 0, 0, ]

    target_points_in_robot_sys = [(pos_list[i], ori_list[i]) for i in selected_idx]
    target_point_in_robot_sys = target_points_in_robot_sys[50]

    # target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((0,-0.3,0.5),(0,0,0, 1))
    joints = sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys[0], target_point_in_robot_sys[1],
                                                     start=None, maxNumIteration=10000, tcp_name="rolling_tool")
    goal = joints
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)

    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal)
    sim_env.robot_list[0].set_joints_states(goal)

    start = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933, -1.8410220234890533,
             -0.6757545624540242]
    path = []
    pairs = zip(pos_list[10000:], ori_list[10000:])
    total_steps = min(len(pos_list[10000:]), len(ori_list[10000:]))
    collision_detect = False
    if collision_detect:
        for i, (pos, ori) in enumerate(tqdm(pairs, total=total_steps, desc="Planning path")):
            sim_env.step_simulation()
            joints = sim_env.robot_list[0].get_state_from_ik(pos,
                                                             ori,
                                                             start=start, maxNumIteration=10000, tcp_name="rolling_tool")
            sim_env.robot_list[0].set_joints_states(joints)

            # print(f"Moving to point {pos}, joints: {joints}")
            # collision
            safe = sim_env.pb_ompl_interface.is_state_valid(joints)
            if not safe:
                print(f"Collision detected at step {len(path)} for joints: {joints}")
                # time.sleep(1)

            path.append(joints)
            # time.sleep(0.1)
    else:
        start = start
        for i, (pos, ori) in enumerate(tqdm(pairs, total=total_steps, desc="Planning path")):
            joints = sim_env.robot_list[0].get_state_from_ik(pos,
                                                             ori,
                                                             start=start, maxNumIteration=10000,
                                                             tcp_name="rolling_tool")
            start = joints

            path.append(joints)
            # time.sleep(0.1)
    np.save("./path_files/滚压_path_01mm_for_新装置.npy", np.array(path))
    print(f"Saved executed path with {len(path)} points to ./path_files/滚压_path_01mm_for_新装置.npy")
    time.sleep(2)

    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            # sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()


def debug_path():
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    machine_state = scene_config["machine_state_A"]
    sim_env.machine.set_joints_states(machine_state)
    for _ in range(100):
        sim_env.step_simulation()

    joints = np.load("/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/path_files/滚压_path_01mm_for_新装置.npy")

    goal = joints[789]
    # 设置机械臂/机床的初始位置
    start = [0.10568717528231546, -0.4105353654619583, -1.1813494586720104, 0.03241272300551933, -1.8410220234890533,
             -0.6757545624540242]
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)

    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal)
    sim_env.robot_list[0].set_joints_states(goal)

    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            # sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()

    sim_env.robot_list[0].set_joints_states(goal)

    for i,joint in enumerate(joints[789:]):

        sim_env.robot_list[0].set_joints_states(joint)

        # print(f"Moving to point {pos}, joints: {joints}")
        # collision
        safe = sim_env.pb_ompl_interface.is_state_valid(joint)
        if not safe:
            print(f"Collision detected at step {i} for joints: {joint}")
            time.sleep(1)

        time.sleep(1/240.)



if __name__ == '__main__':
    # test_point()
    # highlight_points()
    # export_path()
    debug_path()
