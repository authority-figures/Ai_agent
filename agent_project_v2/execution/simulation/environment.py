
import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

from execution.simulation import pb_ompl,taskspaceRRT

from calibrator import *
PI = np.pi
from scipy.interpolate import CubicSpline
import threading

# os.environ["QT_PLUGIN_PATH"] = ""
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_platform_path
os.environ["QT_QPA_PLATFORM"] = ""
print("PYTHON:", sys.executable)
print("QT_PLUGIN_PATH:", os.environ.get("QT_PLUGIN_PATH"))
print("QT_QPA_PLATFORM:", os.environ.get("QT_QPA_PLATFORM"))
print("DISPLAY:", os.environ.get("DISPLAY"))


class SimulationEnvironment:
    def __init__(self, options=""):
        self.options = options
        self.physics_client = None
        self.running = False
        self.time_step = 1 / 240  # 仿真步进时间
        self.robot_id = None
        self.robot_list : list[pb_ompl.PbOMPLRobot|Robot] = []
        self.object_list = []
        self.camera_open = False
        self.base_axis = []
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # 仿真线程属性
        self.simulation_time = 0.0
        self.is_running = False
        self.simulation_thread = None

        # self.simulation_callbacks = []  # 存储热插入的回调函数
        self.simulation_callbacks = {}  # 使用字典存储回调，键是回调的标识符




    def clear_env(self):
        """ 清空仿真环境 """
        for object_id in self.object_list:
            p.removeBody(object_id)

    def initialize(self):
        """ 初始化仿真环境 """
        # 重置仿真环境
        if self.physics_client is not None:
            p.disconnect()
        self.physics_client = p.connect(p.GUI_SERVER, key=1234, options=self.options)  # GUI 模式
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1,
                                   physicsClientId=self.physics_client)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI,0, physicsClientId=self.physics_client) # 关闭GUI信息展示

        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.physics_client)  # 设置搜索路径
        p.loadURDF("plane.urdf", physicsClientId=self.physics_client)  # 加载平面
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
        robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool_12mm.urdf"
        robot_with_rolling_tool_urdf = os.path.join(self.base_path, robot_with_rolling_tool_urdf)
        machine = Machine(self.physics_client)
        self.machine = machine
        self.machine.load_urdf(fileName=machine_file_name, basePosition=(0, 0, 0), useFixedBase=1, flags=0, )
        self.object_list.append(self.machine.id_robot)
        self.workpiece_pose = [0.0, 0.06, 0.04]
        orientation = [0.0, 0.0, 0.0]
        quaternion = p.getQuaternionFromEuler(orientation,physicsClientId=self.physics_client)
        self.workpiece_orientation = quaternion
        self.workpiece_id = self.machine.add_workpiece_to_machine(workpiece_urdf, position=self.workpiece_pose,
                                                             orientation=orientation)

        # self.object_list.append(self.workpiece_id)
        robot_id = self.load_robot(urdf_path=robot_with_rolling_tool_urdf, basePosition=(-0.16, -0.15, 0.7),
                                   baseOrientation=(0.7, 0, 0, 0.7), useFixedBase=0,
                                   start=[0, 0, PI / 2, 0, 0, 0], )
        # 消除执行器于机械臂末端的碰撞
        p.setCollisionFilterPair(robot_id, robot_id, 5, 7, 0,physicsClientId=self.physics_client)
        p.setCollisionFilterPair(robot_id, robot_id, 5, 8, 0,physicsClientId=self.physics_client)
        p.setCollisionFilterPair(robot_id, robot_id, 4, 8, 0,physicsClientId=self.physics_client)

        # 设置机械臂-rolling_tools的tcp坐标
        ee_pos,ee_orn = p.getLinkState(robot_id, 6,physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 10,physicsClientId=self.physics_client)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn,ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool",tcp_in_ee_matrix)
        ee_pos, ee_orn = p.getLinkState(robot_id, 6,physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(robot_id, 7,physicsClientId=self.physics_client)[4:6]
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("rolling_tool_base", tcp_in_ee_matrix)

        self.robot_list[0].inverse_mode = "body_sys"

        # 加载物理相机
        cam_urdf = "./models/camera/urdf/camera.urdf"
        cam_urdf = os.path.join(self.base_path, cam_urdf)
        self.camera = Robot(self.physics_client)
        self.camera.load_urdf(fileName=cam_urdf, basePosition=(0.05, -0.10, 0.75),
                         baseOrientation=p.getQuaternionFromEuler([1.57, 0, 0]), useFixedBase=0)

        # 配置系统
        self.rm_sys = RM_sys(self.robot_list, self.physics_client)


        # 绑定机床到机械臂
        self.rm_sys.init_machine(self.machine, type='velocity')
        self.rm_sys.create_constrain(self.machine,self.robot_list[0],parentPosition=[-0.2, +0.1, 0.08], childOrientation=[0.7068252, 0, 0, 0.7073883]
                                     ,workpiece_pos=self.workpiece_pose,workpiece_ori=self.workpiece_orientation)
        self.rm_sys.init_robot(self.robot_list[0])

        # 加载标定板
        board_urdf = "./models/calibration_board/urdf/calibration_board.urdf"
        board_urdf = os.path.join(self.base_path, board_urdf)
        self.board = Calibration_board(self.physics_client,board_urdf)
        self.rm_sys.robot_list.append(self.board)
        self.rm_sys.robot_list.append(self.machine.workpiece)
        pos, ori = self.rm_sys.get_point_in_workpiece2world([0.05, -0.05, 0.12],
                                                            p.getQuaternionFromEuler([0, 0, PI/2],physicsClientId=self.physics_client))
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
        ee_pos, ee_orn = p.getLinkState(robot_id, 6,physicsClientId=self.physics_client)[4:6]
        tcp_pos, tcp_orn = p.getLinkState(self.camera.id_robot, 3,physicsClientId=self.physics_client)[4:6]  # RGB_Link
        tcp_in_ee_matrix = self.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn, ee_pos, ee_orn)
        self.robot_list[0].add_tcp("RGB_camera", tcp_in_ee_matrix)



        # setup pb_ompl
        self.obstacles = []
        # self.pb_ompl_interface = pb_ompl.PbOMPL(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface = taskspaceRRT.TaskSpaceRRT(self.robot_list[0], self.obstacles)
        self.pb_ompl_interface.set_planner("RRT")
        self.obstacles.extend([self.workpiece_id,self.machine.id_robot])
        self.pb_ompl_interface.set_obstacles(self.obstacles)
        # 消除ompl规划时link4与link8的碰撞
        self.pb_ompl_interface.check_link_pairs.remove((4,8))
        self.pb_ompl_interface.check_link_pairs.remove((4, 9))

        # 设置九点标定
        self.calibration_pather = CalibrationPather(self.robot_list[0], self.pb_ompl_interface)
        self.calibrator : HandEyeCalibrator|None = None

        pass

    def step_simulation(self):
        """ 进行仿真步进 """
        p.stepSimulation(physicsClientId=self.physics_client)

    def show_axis(self, ifshow=True):
        """显示坐标轴"""
        axis_length = 2.0
        if self.base_axis:
            for line_id in self.base_axis:
                p.removeUserDebugItem(line_id,physicsClientId=self.physics_client)
            self.base_axis = []
        if not ifshow:
            return
         # X轴红色，Y轴绿色，Z轴蓝色

        x = p.addUserDebugLine([0, 0, 0], [axis_length, 0, 0], [1, 0, 0], lineWidth=2, lifeTime=0,physicsClientId=self.physics_client)
        y = p.addUserDebugLine([0, 0, 0], [0, axis_length, 0], [0, 1, 0], lineWidth=2, lifeTime=0,physicsClientId=self.physics_client)
        z = p.addUserDebugLine([0, 0, 0], [0, 0, axis_length], [0, 0, 1], lineWidth=2, lifeTime=0,physicsClientId=self.physics_client)
        self.base_axis = [x, y, z]

    def clear_obstacles(self):
        for obstacle in self.obstacles:
            p.removeBody(obstacle,physicsClientId=self.physics_client)

    def add_object(self, urdf_path,  basePosition,baseOrientation,useFixedBase):
        """ 向仿真环境添加物体 """
        if basePosition is None:
            basePosition = [0, 0, 0]
        if baseOrientation is None:
            baseOrientation = [0, 0, 0, 1]
        obj_id = p.loadURDF(urdf_path, basePosition=basePosition, baseOrientation=baseOrientation,useFixedBase=useFixedBase,physicsClientId=self.physics_client)
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
                                                           physicsClientId=self.physics_client
                                                            )
        except Exception as e:
            print(e)
            return "IK failed"

        try:
            for i in range(min(len(joint_positions), robot.num_avail_joints)):
                p.setJointMotorControl2(
                    robot.id_robot, robot.ids_avail_joints[i], p.POSITION_CONTROL,maxVelocity=maxVelocity, targetPosition=joint_positions[i],
                    physicsClientId=self.physics_client
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
                positionGain=0.4, velocityGain=0.8,physicsClientId=self.physics_client
            )
        return "Robot moved successfully"
    def set_robot(self, robot_id,joint_positions):
        """ 控制机械臂的关节 """
        if robot_id is None:
            return "No robot loaded"

        robot = [robot for robot in self.robot_list if robot.id_robot == robot_id][0]
        for i in range(min(len(joint_positions), robot.num_avail_joints)):
            p.resetJointState(
                robot_id, robot.ids_avail_joints[i], targetValue=joint_positions[i],
                physicsClientId=self.physics_client
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
            halfExtents=half_extents,
            physicsClientId=self.physics_client
        )

        # 创建视觉形状
        visual_shape = p.createVisualShape(
            shapeType=p.GEOM_BOX,
            halfExtents=half_extents,
            rgbaColor=color,
            physicsClientId=self.physics_client
        )

        # 创建多体对象（立方体）
        cube_id = p.createMultiBody(
            baseMass=mass,
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=visual_shape,
            basePosition=position,
            baseOrientation=orientation,
            physicsClientId=self.physics_client
        )
        self.object_list.append(cube_id)

        return cube_id

    def get_object_pos_and_ori(self,object_id):
        """
        获取给定 ID 物体的位置

        :param object_id: 物体的 ID
        :return: 物体的位置，格式为 [x, y, z]
        """
        position, ori = p.getBasePositionAndOrientation(object_id,physicsClientId=self.physics_client)
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

    def calibration_from_data(self,calibration_data):
        # 进行标定
        K = calibration_data['camera_matrix']
        D = calibration_data.get('dist_coeffs',None)

        self.calibrator = HandEyeCalibrator(
                                            dist_coeffs=D,
                                            camera_matrix=K,
                                            pattern_size=(7, 7),
                                            square_size=0.002,
                                            asymmetric=False)

        for key in calibration_data['point_data'].item().keys():
            print("添加点：", key)
            point_data = calibration_data['point_data'].item()[key]
            image = point_data['img']
            T = point_data['TB2E']
            img = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            self.calibrator.add_sample_from_image(img, T)

        # 标定
        T = self.calibrator.calibrate()
        print("\n[✓] 相机 -> 末端变换:\n", T)
        print("\n[✓] 标定板 -> 机械臂基座变换:\n", self.calibrator.get_target2base())
        self.robot_list[0].add_tcp("RGB_camera", T)

    def ninePoints_calibration(self,center_joints):
        # 进行采样
        self.ninePoints_sample(center_joints)
        data_path = "./datas/calibration_datas/calibration_data.npz"
        data_path = os.path.join(self.base_path, data_path)


        # 进行标定
        calibration_data = np.load(data_path,allow_pickle=True)
        self.calibration_from_data(calibration_data)

        pass

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
            robot_end_mass = Robot.get_com_in_link_frame(robot.id_robot, 5,physicsClientId=self.physics_client)
            robot_end_in_mass_sys = np.array(pos_in_robot_end_link) - np.array(robot_end_mass)

            camera_mass = Robot.get_com_in_link_frame(camera.id_robot, 3,physicsClientId=self.physics_client)
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
                                               physicsClientId=self.physics_client
                                               )

            p.changeConstraint(constraint_id, maxForce=1e6,physicsClientId=self.physics_client )
            # # p.changeConstraint(constraint_id,  erp=0.2)
            for i in range(camera.id_end_effector + 1):
                p.setCollisionFilterPair(camera.id_robot, robot.id_robot, i, robot.id_end_effector,
                                         0,
                                         physicsClientId=self.physics_client)
                p.changeDynamics(camera.id_robot, i, mass=0.00001,physicsClientId=self.physics_client)
            for i in range(robot.num_all_joints + 1):
                p.setCollisionFilterPair(camera.id_robot, robot.id_robot, -1, i,
                                         0,
                                         physicsClientId=self.physics_client)
            #
            p.setCollisionFilterPair(camera.id_robot, robot.id_robot, -1, robot.id_end_effector,
                                     0,
                                     physicsClientId=self.physics_client)
            #
            p.changeDynamics(camera.id_robot, -1, mass=0.001,physicsClientId=self.physics_client)
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





    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def start_simulation(self, real_time=True):
        """启动仿真"""
        if self.is_running:
            return

        self.is_running = True

        if real_time:
            # 实时仿真模式
            self.simulation_thread = threading.Thread(target=self._simulation_loop)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
        else:
            # 非实时模式（步进）
            self._step_simulation()

    def stop_simulation(self):
        """停止仿真"""
        self.is_running = False
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join()

    def reset_simulation(self):
        """重置仿真"""
        self.stop_simulation()
        p.resetSimulation(physicsClientId=self.physics_client)
        self.objects = {}
        self.robots = {}
        self.simulation_time = 0.0
        # 重新添加地面
        self.ground_id = p.loadURDF("plane.urdf",physicsClientId=self.physics_client)


    def _simulation_loop(self):
        """仿真主循环"""
        while self.is_running:
            self._step_simulation()
            time.sleep(1 / 240)  # 约240Hz

    def _step_simulation(self):
        """执行一步仿真"""
        p.stepSimulation(physicsClientId=self.physics_client)
        # 创建字典副本来避免在迭代时修改字典
        callbacks_copy = list(self.simulation_callbacks.values())
        # 执行所有注册的回调函数（热插入的自定义操作）
        for callback in callbacks_copy:
            callback()

        self.simulation_time += 1 / 240

    def disconnect(self):
        """断开物理引擎连接"""
        self.stop_simulation()
        p.disconnect(self.physics_client)

    def add_simulation_callback(self, callback, callback_id):
        """动态添加回调函数并通过唯一的标识符进行管理"""
        if callable(callback):
            self.simulation_callbacks[callback_id] = callback
        else:
            raise ValueError("callback must be callable")

    def remove_simulation_callback(self, callback_id):
        """移除指定标识符的回调函数"""
        if callback_id in self.simulation_callbacks:
            del self.simulation_callbacks[callback_id]
        else:
            print(f"Warning: Callback with ID {callback_id} not found in the list.")

    def remove_all_DebugItems(self):
        """移除所有调试项"""
        p.removeAllUserDebugItems(physicsClientId=self.physics_client)


def test_ompl():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 1, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582-1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]

    target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((-0.003,-0.0,0.07),(0.0005629,0.706825,0.707388,0.0005633))
    # target_point_in_robot_sys = sim_env.rm_sys.get_point_in_workpiece2robot((0,-0.3,0.5),(0,0,0, 1))
    joints=sim_env.robot_list[0].get_state_from_ik(target_point_in_robot_sys[0],target_point_in_robot_sys[1],start=None,maxNumIteration=10000,tcp_name="rolling_tool")
    goal = joints
    # 设置机械臂/机床的初始位置
    sim_env.robot_list[0].set_state(start)
    sim_env.robot_list[0].set_joints_states(start)
    sim_env.machine.set_joints_states([0.0, -0.0, 0.4, 0.4, 0.0])

    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal)
    sim_env.robot_list[0].set_joints_states(goal)

    for _ in range(100):
        sim_env.step_simulation()
        # time.sleep(sim_env.time_step)
    time.sleep(2)


    # 执行规划
    sim_env.pb_ompl_interface.get_T_goal(goal,tcp_name="rolling_tool")
    sim_env.pb_ompl_interface.z_range = (0.01, 0.2)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.01,0.01)
    sim_env.pb_ompl_interface.y_range = (-0.001,0.001)
    sim_env.pb_ompl_interface.yaw_range = 30
    sim_env.pb_ompl_interface.roll_range = 5
    sim_env.pb_ompl_interface.pitch_range = 5
    sim_env.pb_ompl_interface.set_tsRRT_sample()
    sim_env.pb_ompl_interface.set_planner("RRTConnect")
    # sim_env.pb_ompl_interface.set_state_sampler(taskspaceRRT.MixedValidStateSampler(sim_env.pb_ompl_interface.si, sim_env.pb_ompl_interface.sample_in_task_space, ratio=0.8))
    res, path = sim_env.pb_ompl_interface.plan(goal)


    # robot_id = sim_env.load_robot(r"./models/jaka_description/urdf/jaka_minicobo.urdf",None,None,False)
    # sim_env.move_robot_to_target(robot_id,[0.2,0.3,0.3],[0,0,0,1],10)

    # sim_env.move_robot(robot_id,np.array([0,0,1.57,0,0,0]))
    import threading
    def run_simulation():
        while True:
            sim_env.step_simulation()
            # sim_env.robot_list[0].show_link_sys(7, -1, 1)
            time.sleep(sim_env.time_step)  # 控制仿真步进时间
            sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
            sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")
            sim_env.machine.workpiece.show_link_sys(-1, -1, 1, name="3")
            sim_env.rm_sys.update_cam_pos()

    simulation_thread = threading.Thread(target=run_simulation, )
    simulation_thread.start()
    if res:
        sim_env.pb_ompl_interface.execute(path, dynamics=True)


def test_ikpy():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    # rm_sys = RM_sys([], sim_env.physics_client)
    robot_urdf = r"./models/jaka_description/urdf/jaka_minicobo.urdf"
    robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool.urdf"
    robot_id = sim_env.load_robot(robot_with_rolling_tool_urdf, (0,0,1), None, True)
    sim_env.robot_list[0].set_joints_states([0, 0, PI/2, 0, 0, 0])
    p.setCollisionFilterPair(robot_id, robot_id, 5, 7, 0)
    p.setCollisionFilterPair(robot_id, robot_id, 5, 8, 0)
    p.setCollisionFilterPair(robot_id, robot_id, 4, 8, 0)

    # 设置机械臂的tcp坐标
    ee_pos, ee_orn = p.getLinkState(robot_id, 6)[4:6]
    tcp_pos, tcp_orn = p.getLinkState(robot_id, 10)[4:6]
    tcp_in_ee_matrix = sim_env.robot_list[0].TAB_with_AinW_and_BinW(tcp_pos, tcp_orn,ee_pos, ee_orn)
    sim_env.robot_list[0].add_tcp("rolling_tool", tcp_in_ee_matrix)



    targetPos, targetOrn = [0.2,0.25,0.1], [1, 0, 0, 0.00079]
    tcp_in_W_matrix = sim_env.robot_list[0].pos_to_matrix(targetPos, targetOrn)
    ee_in_W_matrix = sim_env.robot_list[0].transform_tcp_target_to_ee_target(tcp_in_W_matrix, "rolling_tool")
    pos,ori = sim_env.robot_list[0].matrix_to_pos(ee_in_W_matrix)
    sim_env.robot_list[0].inverse_mode = "body"
    joints = sim_env.robot_list[0].get_state_from_ik(pos,ori,start=[0,0,0,0,0,0],maxNumIteration=10000)
    sim_env.robot_list[0].set_joints_states(joints)

    pos1,ori1=sim_env.robot_list[0].show_link_sys(10, -1, 1, name="1")
    print(pos1,ori1)



def debug():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    # rm_sys = RM_sys([], sim_env.physics_client)
    robot_urdf = r"./models/jaka_description/urdf/jaka_minicobo.urdf"
    robot_with_rolling_tool_urdf = r"./models/jaka_description/urdf/jaka_minicobo_with_rolling_tool.urdf"
    robot_id = sim_env.load_robot(robot_urdf, None, None, True)
    sim_env.robot_list[0].set_joints_states([0, 0, 0, 0, 0, 0])
    p.setCollisionFilterPair(robot_id, robot_id, 5, 7, 0)
    p.setCollisionFilterPair(robot_id, robot_id, 5, 8, 0)
    p.setCollisionFilterPair(robot_id, robot_id, 4, 8, 0)

    # rm_sys.init_robot(sim_env.robot_list[0])
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582-1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    sim_env.move_robot(robot_id, [0, 0, 0, 0, 0, 0])

    sim_env.robot_list[0].show_link_sys(5, -1, 1, name="2")

    while sim_env.running:
        sim_env.step_simulation()
        # sim_env.robot_list[0].show_link_sys(9, -1, 1,name="1")
        sim_env.robot_list[0].show_link_sys(5, -1, 1,name="2")

        time.sleep(sim_env.time_step)  # 控制仿真步进时间

def debug_cam():
    import time
    sim_env = SimulationEnvironment()
    sim_env.initialize()
    sim_env.load_scene()

    target_j = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582]

    start = [1.57, 0, 1, 0, 0, 0, ]
    # start = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098+1.57, -0.7582-1.01229]
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -0.7582 - 1.01229]  # 关节六于之前定义的0位置之间的偏差为现0=原0-1.01229
    goal = [0.0272, 0.0179, -1.8492, 0.0019, -1.3098, -1.77049]

    target_point_in_robot_sys1 = sim_env.rm_sys.get_point_in_workpiece2robot((0.12, -0.05, 0.12),
                                                                            (0,0.7071068,0,-0.7071068))

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
    sim_env.rm_sys.init_machine(sim_env.machine,'pos',[0.0, -0.0, 0.5, 0.4, -0.05,0])

    # sim_env.robot_list[0].set_joints_states(goal1)
    # sim_env.move_robot(sim_env.robot_list[0].id_robot, goal1)


    for _ in range(100):
        sim_env.step_simulation()
        # time.sleep(sim_env.time_step)
    time.sleep(2)

    # 执行规划
    sim_env.pb_ompl_interface.z_range = (0.01, 0.2)  # z-axis range for sampling
    sim_env.pb_ompl_interface.x_range = (-0.01, 0.01)
    sim_env.pb_ompl_interface.y_range = (-0.01, 0.01)
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
    test_ompl()
    # debug_cam()
    # test_ikpy()
    # debug()
