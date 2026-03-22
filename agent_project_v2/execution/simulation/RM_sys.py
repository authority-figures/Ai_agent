import time

import numpy as np
import pybullet as p

import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

from Robot import Robot
from Machine import Machine
from Gripper import Gripper
from Camera import Camera
from scipy.spatial.transform import Rotation as R


import re
import copy
from tqdm import tqdm
from pyquaternion import Quaternion
from my_utils import invert_quaternion
PI=np.pi

class RM_sys:
    # 创建pybullet连接
    def __init__(self,robot_list=[], id_client=None):

        self.robot_list = robot_list
        self.id_client = id_client
        self.T_workpiece2robot = None
        self.T_workpiece2world = None
        self.T_board2workpiece = None
        self.camera = None
        self.robot_constrain = None
        pass


    # def default_init(self):
    #     self.id_client = p.connect(p.GUI)
    #     p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1,
    #                                physicsClientId=self.id_client)
    #     p.setAdditionalSearchPath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../RobotDir/urdf/'))
    #     self.env = PybulletEnv(id_client=self.id_client)
    #     # workpiece_urdf = r"F:\sw\urdf_files\6061_simple\urdf\6061_simple.urdf"
    #     workpiece_urdf = r"F:\sw\urdf_files\6061_C_continue\urdf\6061_C_continue.urdf"
    #     machine_file_name = "F:\sw\\urdf_files\c501-simple.SLDASM\\urdf\c501-simple.SLDASM.urdf"
    #     # machine_file_name = "F:\sw\\urdf_files\mikron\\urdf\mikron.urdf"
    #     # robot_urdf = "F:\sw\\urdf_files\i7-nofork.SLDASM\\urdf\i7-nofork.SLDASM.urdf"
    #     # robot_urdf = "F:\sw\\urdf_files\Aubo_i3\\urdf\Aubo_i3.urdf"
    #     # robot_urdf = r"F:\sw\\urdf_files\SR3-C\\urdf\SR3-C.urdf"
    #     # robot_urdf = r"F:\sw\\urdf_files\jaka_mini\\urdf\jaka_mini.urdf"
    #     robot_urdf = r"F:\sw\urdf_files\minicobo_v1.4\urdf\minicobo_v1.4.urdf"
    #
    #     machine = Machine(self.id_client)
    #     machine.load_urdf(fileName=machine_file_name, basePosition=(0, 0, 0), useFixedBase=1, flags=0, )
    #     self.init_machine(type='p')
    #     self.workpiece_pose = [0.0, 0.1, 0.00]
    #     orientation = [0.0, 0.0, 0.]
    #     quaternion = p.getQuaternionFromEuler(orientation)
    #     self.workpiece_orientation = quaternion
    #     self.workpiece_id = machine.add_workpiece_to_machine(workpiece_urdf, position=self.workpiece_pose,
    #                                                               orientation=orientation)
    #
    #     self.env.load_robot(fileName=robot_urdf, basePosition=(-0.15, -0.15, 0.7), useFixedBase=0,
    #                         # flags=p.URDF_USE_SELF_COLLISION,
    #                         start=[0, 0, PI / 2, 0, 0, 0],)
    #     self.create_constrain(machine,robot,parentPosition=[-0.2, +0.1, 0.08], childOrientation=[0.7068252, 0, 0, 0.7073883])
    #
    #     rolling_tool = Gripper(self.id_client)
    #     rolling_tool.load_urdf(fileName="F:\\sw\\urdf_files\\rolling_tool\\urdf\\rolling_tool.urdf",
    #                                 basePosition=(-1, -1, 1), useFixedBase=0, flags=0)
    #     self.bind_rolling_tool2robot(robot, rolling_tool, pos_in_robot_end_link=[0, 0, 0], )
    #     self.init_rolling_tool()
    #     self.init_robot()
    #
    #     tool_id = machine.add_tool_to_machine("F:\\sw\\urdf_files\\tool_6mm.SLDASM\\urdf\\tool_6mm.SLDASM.urdf"
    #                                                , tool_length=0.15)
    #     p.setCollisionFilterPair(self.workpiece_id, tool_id, -1, -1, 0)
    #     self.nc_code_path = "F:\\UG\\blade\\NC_1.tp"
    #     machine.parse_nc_code(
    #         # "F:\\python\\python-vtk\\pybulletProject\\cutting_with_rolling\\data\\tp_path.txt",
    #         # r"F:\sw\滚压\用作机械臂\边切边滚实验方案\ug\6061_simple_精加工-连续.tp",
    #         # r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\机床路径凹面1.tp",
    #         # r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\机床路径凸面1.tp",
    #         # r"F:\sw\滚压\用作机械臂\边切边滚实验方案\ug\test\测试A轴标准.tp"
    #         # r"F:\sw\滚压\用作机械臂\边切边滚实验方案\ug\test\新pui新刀位_移除机床.tp"
    #         # r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\6061_C轴连续加工.tp",
    #         r'F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\3595A_刀路.tp',
    #     )
    #
    #     self.joint_values = machine.get_values_with_nc_codes()
    #     # self.joint_values = machine.interpolation_path((np.array(self.joint_values)), scale=10,id_index=-1)  # 最后一项为编号
    #     robot_goto_positions = self.read_cls_file(r'F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\6061_simple中面刀位.cls',inverse=True)
    #
    #
    #     self.debug()
    #
    #     pass

   
    def init_machine(self,machine, type='velocity',init_pos=None):
        machine.set_id_end_effector(4)
        if init_pos is None:
            init_pos = [0, 0, -0.6, -0.2, 0, 0]
        self.new_joint_ranges = [(None, None), (None, None), (init_pos[2], None), (init_pos[3], None), (None, None),
                                 (None, None)]
        machine.set_joint_ranges(self.new_joint_ranges)
        machine.set_joints_states(init_pos)
        for i in range(machine.num_all_joints):
            p.changeDynamics(
                bodyUniqueId=machine.id_robot,
                linkIndex=i,
                jointDamping=0.2,
                mass=10,
                linearDamping=0.5, angularDamping=0.5,
                physicsClientId=self.id_client
            )
        force = 10000
        if type == 'velocity':
            mode = p.VELOCITY_CONTROL
            p.setJointMotorControl2(machine.id_robot, 0, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 1, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 2, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 3, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 4, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 5, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        else:
            mode = p.POSITION_CONTROL
            p.setJointMotorControl2(machine.id_robot, 0, mode, targetPosition=init_pos[0], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 1, mode, targetPosition=init_pos[1], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 2, mode, targetPosition=init_pos[2], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 3, mode, targetPosition=init_pos[3], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 4, mode, targetPosition=init_pos[4], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)
            p.setJointMotorControl2(machine.id_robot, 5, mode, targetPosition=init_pos[5], targetVelocity=0,
                                    force=force,physicsClientId=self.id_client)

    def init_robot(self,robot):
        # for i in range(robot.num_avail_joints):
        #     p.resetJointState(robot.id_robot,i,0)
        robot.set_joints_states([0, 0, 0, 0, 0, 0])
        robot.inverse_mode = 'body_sys'
        for i in range(robot.num_avail_joints):
            p.changeDynamics(
                bodyUniqueId=robot.id_robot,
                linkIndex=robot.ids_avail_joints[i],
                jointDamping=0.1,
                mass=0.1,
                angularDamping=0.5,
                physicsClientId=self.id_client

            )

        # for joint in range(6):
        #     p.changeDynamics(robot.id_robot, joint, linearDamping=0.1, angularDamping=0.5)

        force = 10000
        mode = p.VELOCITY_CONTROL
        p.setJointMotorControl2(robot.id_robot, 0, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        p.setJointMotorControl2(robot.id_robot, 1, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        p.setJointMotorControl2(robot.id_robot, 2, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        p.setJointMotorControl2(robot.id_robot, 3, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        p.setJointMotorControl2(robot.id_robot, 4, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)
        p.setJointMotorControl2(robot.id_robot, 5, mode, targetVelocity=0, force=force,physicsClientId=self.id_client)

        # for i in range(robot.id_end_effector):
        #     p.changeDynamics(robot.id_robot, i, mass=10)
        for _ in range(100):
            p.stepSimulation(physicsClientId=self.id_client)
            # time.sleep(1/240.)
        pass

    def init_rolling_tool(self,rolling_tool):

        rolling_tool.set_joints_states([0, 0])
        for i in range(rolling_tool.num_all_joints):
            p.changeDynamics(
                bodyUniqueId=rolling_tool.id_robot,
                linkIndex=i,
                jointDamping=0.2,
                mass=0.01,
                linearDamping=0.5, angularDamping=0.5,physicsClientId=self.id_client
            )
        force = 100000
        mode = p.POSITION_CONTROL
        p.setJointMotorControl2(rolling_tool.id_robot, 0, mode, targetPosition=0, targetVelocity=0,
                                positionGain=0.5,  # KP
                                velocityGain=0.5,  # KD
                                force=force, physicsClientId=self.id_client)
        p.setJointMotorControl2(rolling_tool.id_robot, 1, mode, targetPosition=0, targetVelocity=0,
                                positionGain=0.5,  # KP
                                velocityGain=0.5,  # KD
                                force=force, physicsClientId=self.id_client)

        pass

    def bind_rolling_tool2robot(self, robot: Robot, gripper: Gripper, pos_in_robot_end_link=[0, 0, 0],
                                pos_in_gripper_base_link=[0, 0, 0],physicsClientId=None):

        if physicsClientId is None:
            raise ValueError("Physics client ID cannot be None.")
        robot_end_mass = Robot.get_com_in_link_frame(robot.id_robot, robot.id_end_effector,physicsClientId=self.id_client)
        robot_end_in_mass_sys = np.array(pos_in_robot_end_link) - np.array(robot_end_mass)

        gripper_mass = Robot.get_com_in_link_frame(gripper.id_robot, -1, baseFramePosition=gripper.baseLinkPosition,physicsClientId=self.id_client)
        gripper_in_mass_sys = np.array(pos_in_gripper_base_link) - np.array(gripper_mass)

        constraint_id = p.createConstraint(parentBodyUniqueId=robot.id_robot,
                                           parentLinkIndex=robot.id_end_effector,
                                           childBodyUniqueId=gripper.id_robot,
                                           childLinkIndex=-1,  # 表示连接到工件的基础部分
                                           jointType=p.JOINT_FIXED,  # p.JOINT_POINT2POINT p.JOINT_REVOLUTE
                                           jointAxis=[0, 0, 0],
                                           parentFramePosition=robot_end_in_mass_sys,
                                           childFramePosition=gripper_in_mass_sys,
                                           childFrameOrientation=p.getQuaternionFromEuler((3.14, 0, 1.57 / 2)),
                                           physicsClientId=self.id_client,
                                           )

        p.changeConstraint(constraint_id, maxForce=1e8, physicsClientId=self.id_client)
        p.setCollisionFilterPair(gripper.id_robot, robot.id_robot, -1, robot.id_end_effector, 0,
                                 physicsClientId=physicsClientId)
        self.point_in_ee_frame, self.robot_target_ori = [0, 0, 0.13345], [1.88005569e-11, -6.09188950e-04,
                                                                          3.82499073e-01, 9.23955674e-01]
        for _ in range(200):
            p.stepSimulation(physicsClientId=physicsClientId)

        pass

    def create_constrain(self,machine ,robot, parentPosition=[0, 0, 0], childPosition=[0, 0, 0], childOrientation=[0, 0, 0, 1],workpiece_pos=None, workpiece_ori=None):
        # fixed_joint = p.createConstraint(robot.id_robot, 6, self.env.robots[1].id_robot, -1,
        #                                  p.JOINT_FIXED, [0, 0, 1], [0, 0, 0], [0, 0, 0], physicsClientId=self.id_client)
        childOrientation = invert_quaternion(childOrientation)
        self.robot_constrain = self.createConstraintBase(machine.id_robot, 1, robot.id_robot, -1,
                                                p.JOINT_FIXED, [0, 0, 0], parentPosition, childPosition,
                                                childFrameOrientation=childOrientation,
                                                physicsClientId=self.id_client)

        # p.setCollisionFilterPair(robot.id_robot, self.env.robots[1].id_robot, 0, -1, 0,
        #                          physicsClientId=self.id_client)
        # p.setCollisionFilterPair(robot.id_robot, self.env.robots[1].id_robot, 1, -1, 0,
        #                          physicsClientId=self.id_client)

        p.setCollisionFilterPair(robot.id_robot, machine.id_robot, -1, 0, 0,
                                 physicsClientId=self.id_client)
        p.setCollisionFilterPair(robot.id_robot, machine.id_robot, -1, 1, 0,
                                 physicsClientId=self.id_client)

        # 记录工件坐标系相对于机械臂本体坐标系的位置和姿态，方便将工件坐标系的点转换到机械臂本体坐标系

        if workpiece_pos is not None and workpiece_ori is not None:
            robot_pos = parentPosition
            robot_ori = invert_quaternion(childOrientation)
            # 计算工件坐标系在机械臂坐标系下的表示
            self.T_workpiece2robot = Robot.TAB_with_AinW_and_BinW(workpiece_pos, workpiece_ori, robot_pos, robot_ori)
            # 计算工件坐标系在世界坐标系下的表示 这里均是在C轴坐标系下的表示
            self.T_workpiece2world = Robot.TAB_with_AinW_and_BinW(workpiece_pos, workpiece_ori,[0,0,-machine.C_in_sys0],[0,0,0,1])
            # 计算机器人坐标系在世界坐标系下的表示
            self.T_robot2world = Robot.TAB_with_AinW_and_BinW(robot_pos, robot_ori, [0,0,-machine.C_in_sys0],[0,0,0,1])
        pass


    def bind_board2workpiece(self,workpiece:Robot,board:Robot,parentPosition=[0, 0, 0], childPosition=[0, 0, 0], childOrientation=[0, 0, 0, 1],):
        childOrientation = invert_quaternion(childOrientation)
        fixed_joint = self.createConstraintBase(workpiece.id_robot, -1, board.id_robot, -1,
                                                p.JOINT_FIXED, [0, 0, 0], parentPosition, childPosition,
                                                childFrameOrientation=childOrientation,
                                                physicsClientId=self.id_client)
        # p.createConstraint(workpiece.id_robot, -1, board.id_robot, -1,
        #                                         p.JOINT_FIXED, [0, 0, 0], parentPosition, childPosition,
        #                                         childFrameOrientation=childOrientation,
        #                                         physicsClientId=self.id_client)
        p.changeConstraint(fixed_joint, maxForce=1e8, )
        for _ in range(100):
            p.stepSimulation(physicsClientId=self.id_client)
        workpiece_mass_pos,workpiece_ori = p.getBasePositionAndOrientation(workpiece.id_robot)[0:2]
        workpiece_mass_in_link = workpiece.baseFramePosition
        workpiece_pos = np.array(workpiece_mass_pos) - R.from_quat(workpiece_ori).as_matrix() @ np.array(workpiece_mass_in_link)
        board_pos,board_ori = p.getLinkState(board.id_robot, 0)[4:6]
        self.T_board2workpiece = Robot.TAB_with_AinW_and_BinW(board_pos, board_ori,workpiece_pos, workpiece_ori, )


    def find_robot_by_id(self, robot_id) -> Robot|None:
        for robot in self.robot_list:
            if robot.id_robot == robot_id:
                return robot
        return None

    def createConstraintBase(self, parentBodyUniqueId=None, parentLinkIndex=-1, childBodyUniqueId=None, childLinkIndex=-1,
                         jointType=p.JOINT_FIXED, jointAxis=[0, 0, 0], parentFramePosition=[0, 0, 0],
                         childFramePosition=[0, 0, 0],physicsClientId=None, **kwargs):
        '''
        通用型创建约束
        parentFramePosition: 固定目标点在父link坐标系下的位置
        childFramePosition: 固定目标点在子link坐标系下的位置
        :param args:
        :param kwargs:
            原参数parentBodyUniqueId,parentLinkIndex,childBodyUniqueId,childLinkIndex,jointType,jointAxis,
            parentFramePosition: 固定目标点在父链接的质心坐标系下的坐标,
            childFramePosition: 固定目标点在子链接的质心坐标系下的坐标,
            *parentFrameOrientation,*childFrameOrientation,*physicsClientId
        :return:constraintId
        '''

        # 获取父link的质心坐标
        try:
            if parentLinkIndex == -1:
                parent_robot = self.find_robot_by_id(parentBodyUniqueId)
                parent_mass_coordinate = parent_robot.baseFramePosition
            else:
                parent_mass_coordinate = Robot.get_com_in_link_frame(parentBodyUniqueId, parentLinkIndex,
                                                                     physicsClientId=physicsClientId)

            if childLinkIndex == -1:
                child_robot = self.find_robot_by_id(childBodyUniqueId)
                child_mass_coordinate = child_robot.baseFramePosition
            else:
                child_mass_coordinate = Robot.get_com_in_link_frame(childBodyUniqueId, childLinkIndex,
                                                                    physicsClientId=physicsClientId)
        except Exception as e:

            print(e)
            print("获取质心坐标失败")
            raise

        new_parentFramePosition = [x - y for x, y in zip(parentFramePosition, parent_mass_coordinate)]

        new_childFramePosition = [x - y for x, y in zip(childFramePosition, child_mass_coordinate)]

        parentFramePosition = new_parentFramePosition
        childFramePosition = new_childFramePosition

        constraintId = p.createConstraint(parentBodyUniqueId, parentLinkIndex, childBodyUniqueId, childLinkIndex,
                                          jointType, jointAxis, parentFramePosition, childFramePosition,physicsClientId=physicsClientId, **kwargs)
        return constraintId
        pass

    def set_R_W_M_collision(self,robot:Robot,workpiece_id, machine:Machine, rolling_tool:Gripper):
        for i in range(-1, robot.id_end_effector + 1):
            for j in range(-1, machine.workpiece.num_all_joints + 1):
                p.setCollisionFilterPair(robot.id_robot, workpiece_id, i, j, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_robot, i, 0, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_robot, i, -1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_robot, i, 1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_robot, i, 2, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_tool, i, -1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(robot.id_robot, machine.id_tool, i, 0, 0,physicsClientId=self.id_client)

        for i in range(-1, rolling_tool.num_all_joints + 1):
            for j in range(-1, machine.workpiece.num_all_joints + 1):
                p.setCollisionFilterPair(rolling_tool.id_robot, workpiece_id, i, j, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_robot, i, 0, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_robot, i, -1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_robot, i, 1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_robot, i, 2, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_tool, i, -1, 0,physicsClientId=self.id_client)
            p.setCollisionFilterPair(rolling_tool.id_robot, machine.id_tool, i, 0, 0,physicsClientId=self.id_client)

        for i in range(-1, rolling_tool.num_all_joints + 1):
            for j in range(-1, robot.id_end_effector + 1):
                p.setCollisionFilterPair(rolling_tool.id_robot, robot.id_robot, i, j, 0,physicsClientId=self.id_client)


    def get_point_in_workpiece2robot(self, pos, ori,inverse=False):
        if self.T_workpiece2robot is not None:
            if inverse==False:
                rot = R.from_quat(ori).as_matrix()
                T_p = np.eye(4)
                T_p[:3, :3] = rot
                T_p[:3, 3] = pos
                trans_T = np.dot(self.T_workpiece2robot, T_p)
                trans_pos, trans_ori = trans_T[:3, 3], R.from_matrix(trans_T[:3, :3]).as_quat()
            else:
                rot = R.from_quat(ori).as_matrix()
                T_p = np.eye(4)
                T_p[:3, :3] = rot
                T_p[:3, 3] = pos
                trans_T = np.dot(np.linalg.inv(self.T_workpiece2robot), T_p)
                trans_pos, trans_ori = trans_T[:3, 3], R.from_matrix(trans_T[:3, :3]).as_quat()
            return trans_pos, trans_ori
        else:
            print("机械臂和工件的约束关系未建立")
        pass
    def get_point_in_workpiece2world(self, pos, ori,inverse=False):
        if self.T_workpiece2world is not None:
            if inverse==False:
                rot = R.from_quat(ori).as_matrix()
                T_p = np.eye(4)
                T_p[:3, :3] = rot
                T_p[:3, 3] = pos
                trans_T = np.dot(self.T_workpiece2world, T_p)
                trans_pos, trans_ori = trans_T[:3, 3], R.from_matrix(trans_T[:3, :3]).as_quat()
                return trans_pos, trans_ori
            else:
                rot = R.from_quat(ori).as_matrix()
                T_p = np.eye(4)
                T_p[:3, :3] = rot
                T_p[:3, 3] = pos
                trans_T = np.dot(np.linalg.inv(self.T_workpiece2world), T_p)
                trans_pos, trans_ori = trans_T[:3, 3], R.from_matrix(trans_T[:3, :3]).as_quat()
                return trans_pos, trans_ori
        else:
            print("机械臂和工件的约束关系未建立")
        pass

    def get_work_piece_sys_point_in_world_sys(self, pos=[], ori=[]):
        workpiece_state = p.getLinkState(self.workpiece_id, 0,physicsClientId=self.id_client)
        workpiece_pos = np.array(workpiece_state[4])
        workpiece_ori = np.array(workpiece_state[5])

        # 计算旋转矩阵
        rotation_matrix = np.array(p.getMatrixFromQuaternion(workpiece_ori,physicsClientId=self.id_client)).reshape(3, 3)

        # 构建齐次变换矩阵
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rotation_matrix
        transform_matrix[:3, 3] = workpiece_pos

        world_points = []
        world_orientations = []

        for point, orientation in zip(pos, ori):
            # 将点转换为齐次坐标
            local_point_homogeneous = np.append(point, 1)

            # 进行坐标变换
            world_point_homogeneous = np.dot(transform_matrix, local_point_homogeneous)

            # 提取转换后的点 (x, y, z)
            world_points.append(world_point_homogeneous[:3])

            # 将局部姿态转换为世界姿态
            local_rotation = R.from_quat(orientation)
            world_rotation = R.from_matrix(rotation_matrix) * local_rotation
            world_orientations.append(world_rotation.as_quat())

        return world_points, world_orientations

        pass

    def bind_cam2robot(self, robot: Robot, camera: Robot, pos_in_robot_end_link=[0, 0, 0],
                       pos_in_cam_base_link=[0, 0, 0], ori_in_cam_base_link=[0, 0, 0]):

        robot_end_mass = Robot.get_com_in_link_frame(robot.id_robot, robot.id_end_effector,physicsClientId=self.id_client)
        robot_end_in_mass_sys = np.array(pos_in_robot_end_link) - np.array(robot_end_mass)

        camera_mass = Robot.get_com_in_link_frame(camera.id_robot, -1, baseFramePosition=camera.baseLinkPosition,physicsClientId=self.id_client)
        camera_in_mass_sys = -np.array(camera.baseFramePosition)

        constraint_id = p.createConstraint(parentBodyUniqueId=robot.id_robot,
                                           parentLinkIndex=robot.id_end_effector,
                                           childBodyUniqueId=camera.id_robot,
                                           childLinkIndex=-1,  # 表示连接到工件的基础部分
                                           jointType=p.JOINT_FIXED,  # p.JOINT_POINT2POINT p.JOINT_REVOLUTE
                                           jointAxis=[0, 0, 0],
                                           parentFramePosition=robot_end_in_mass_sys,
                                           childFramePosition=camera_in_mass_sys,
                                           childFrameOrientation=p.getQuaternionFromEuler(ori_in_cam_base_link),
                                           physicsClientId=self.id_client
                                           )

        p.changeConstraint(constraint_id, maxForce=1e6, physicsClientId=self.id_client)
        # # p.changeConstraint(constraint_id,  erp=0.2)
        for i in range(camera.id_end_effector + 1):
            p.setCollisionFilterPair(camera.id_robot, robot.id_robot, i, robot.id_end_effector,
                                     0,
                                     physicsClientId=self.id_client)
            p.changeDynamics(camera.id_robot, i, mass=0.00001)
        for i in range(robot.num_all_joints+1):
            p.setCollisionFilterPair(camera.id_robot, robot.id_robot,-1, i,
                                     0,
                                     physicsClientId=self.id_client)
        #
        p.setCollisionFilterPair(camera.id_robot, robot.id_robot, -1, robot.id_end_effector,
                                 0,
                                 physicsClientId=self.id_client)
        #
        p.changeDynamics(camera.id_robot, -1, mass=0.001,physicsClientId=self.id_client)
        #
        # for _ in range(10):
        #     p.stepSimulation()

        return constraint_id
        pass

    def create_virtual_cams(self, fps=60):
        robot_id = self.robot_list[0].id_robot
        self.left_depth_camera = Camera(robotId=robot_id, width=640, height=480, show_cv=0)
        self.left_depth_camera.focal_length_pixels = 383.3886413574219
        self.right_depth_camera = Camera(robotId=robot_id, width=640, height=480, show_cv=0)
        self.right_depth_camera.focal_length_pixels = 383.3886413574219
        self.RGB_camera = Camera(robotId=robot_id, width=640, height=480, fps=fps, show_cv=1, nearVal=0.05)
        self.right_depth_camera.focal_length_pixels = (606.8582763671875 + 606.9253540039062) / 2
        self.RGB_camera2endEffector_pos = [-0.030383358162982828, 0.04983539700085212, -0.013351126934074722]
        pass

    def reset_cam_fps(self, fps):
        self.RGB_camera.fps = fps
        pass

    def update_cam_pos(self):
        RGB_camera_state = p.getLinkState(self.camera.id_robot, 3,physicsClientId=self.id_client)
        # 获取四元数
        orientation_quat = RGB_camera_state[5]
        # 将四元数转换为旋转矩阵
        rot_matrix = p.getMatrixFromQuaternion(orientation_quat,physicsClientId=self.id_client)
        rot_matrix = np.array(rot_matrix).reshape(3, 3)  # 转换为3x3矩阵
        # 定义局部 z 轴向量
        local_z_axis = np.array([0, 0, 1])
        global_z_axis = rot_matrix.dot(local_z_axis)
        self.RGB_camera.updata_cam_pos_inRobotSys(RGB_camera_state[4], global_z_axis, rot_matrix)
        pass

    def hold_robot_state(self,robot, joint_list: list):
        force = 100
        mode = p.POSITION_CONTROL
        for i, joint in enumerate(joint_list):
            p.setJointMotorControl2(robot.id_robot, i, mode, targetPosition=joint, targetVelocity=0,
                                    positionGain=0.05,  # KP
                                    velocityGain=0.2,  # KD
                                    force=force,
                                    physicsClientId=self.id_client
                                    )
        pass

    def read_cls_file(self, robot, cls_file_path, inverse=False, only_inverse_direction=False):
        """
        读取CLS文件并将其转换为字典格式，同时计算四元数。

        :param cls_file_path: CLS文件路径
        :return: 包含位置和四元数的字典列表
        """
        with open(cls_file_path, 'r') as file:
            lines = file.readlines()

        pattern = re.compile(r'GOTO/([\d\.\-]+),([\d\.\-]+),([\d\.\-]+),?([\d\.\-]*)?,?([\d\.\-]*)?,?([\d\.\-]*)?')

        result = []
        origin_data = []
        last_data = [0, 0, 0, 1, 0, 0]
        for line in lines:
            match = pattern.match(line.strip())
            if match:
                x = float(match.group(1))
                y = float(match.group(2))
                z = float(match.group(3))
                i = float(match.group(4)) if match.group(4) else last_data[3]
                j = float(match.group(5)) if match.group(5) else last_data[4]
                k = float(match.group(6)) if match.group(6) else last_data[5]

                last_data = [x, y, z, i, j, k]

                # 计算四元数
                quat = self.calculate_quaternion(i, j, k, inverse=inverse,
                                                 only_inverse_direction=only_inverse_direction)
                pos, ori = self.get_point_in_workpiece2robot([x / 1000, y / 1000, z / 1000],
                                                             [quat[1], quat[2], quat[3], quat[0], ])
                # pos,ori = robot.calculate_ee_origin_from_target(pos, ori,
                #                                                    self.point_in_ee_frame,
                #                                                    self.robot_target_ori)
                origin_data.append(([x / 1000, y / 1000, z / 1000], [quat[1], quat[2], quat[3], quat[0], ]))
                result.append({
                    'X': pos[0],
                    'Y': pos[1],
                    'Z': pos[2],
                    'O': {'x': ori[0], 'y': ori[1], 'z': ori[2], 'w': ori[3], }
                })

        return result, origin_data
    @staticmethod
    def calculate_quaternion(i, j, k,inverse=False,only_inverse_direction=False):
        """
        根据给定的方向向量计算四元数，使其x轴对齐方向向量，y轴对齐世界坐标系的Z轴。

        :param i: x方向分量
        :param j: y方向分量
        :param k: z方向分量
        :return: 对应的四元数
        """
        # 创建方向向量
        direction = np.array([i, j, k])
        direction_norm = np.linalg.norm(direction)
        if direction_norm == 0:
            raise ValueError("The direction vector cannot be zero.")
        direction = direction / direction_norm

        old_z = np.array([0, 0, 1])

        if inverse:
            direction = -direction
            old_z = -old_z

        if only_inverse_direction:
            # UG生成刀路时刀轴矢量取反了
            direction = -direction

        # 确定新的坐标系的y轴（与世界坐标系Z轴对齐）
        new_y_axis = -old_z

        # 确定新的坐标系的x轴（与方向向量对齐）
        new_x_axis = direction

        # 计算新的坐标系的y轴（新x轴与新z轴的叉积）
        new_z_axis = np.cross(new_x_axis,new_y_axis)
        new_z_axis = new_z_axis / np.linalg.norm(new_z_axis)

        # # 重新计算新的x轴（确保正交性）
        # new_x_axis = np.cross(new_y_axis, new_z_axis)
        # new_x_axis = new_x_axis / np.linalg.norm(new_x_axis)

        # 构建旋转矩阵
        rotation_matrix = np.array([new_x_axis, new_y_axis, new_z_axis]).T

        # 计算四元数
        quat = Quaternion(matrix=rotation_matrix)
        return quat

    def convert_positions_to_joints(self,robot:Robot,robot_goto_positions=None ,start=None,save=False,filename="joints_list.npy"):
        """
        读取sys.robot_goto_positions中的位置和四元数，调用calc_path_joints函数，将其转换为关节列表。

        :param sys: 系统对象，包含机器人和环境信息
        :param start: 初始位置（可选）
        :return: 包含关节列表的列表
        """
        joints_list = []
        if robot_goto_positions is None:
            robot_goto_positions = robot_goto_positions


        for item in tqdm(robot_goto_positions,desc="convert_positions_to_joints:计算机械臂刀位点路径"):
            # 提取位置和四元数
            robot_target_pos = [item['X'], item['Y'], item['Z']]
            robot_target_ori = [item['O']['x'], item['O']['y'], item['O']['z'],item['O']['w']]
            # 为什么会多出来0？
            # 计算路径关节
            joints = robot.get_state_from_ik(robot_target_pos,robot_target_ori,start=start)
            start = list(copy.deepcopy(joints))
            joints_list.append((joints))
        print("计算完成,共计", len(joints_list), "个点。")
        if save:
            np.save(f"F:\\python\\RobotGUI_2.1\\User_Defined_Demos\\Robot_Machine\\files\\{filename}", joints_list)
            print(f"已保存为{filename}")

        return joints_list


def timer(func):
    def func_wrapper(*args, **kwargs):
        from time import time
        time_start = time()
        result = func(*args, **kwargs)
        time_end = time()
        time_spend = time_end - time_start
        print('{0} cost time {1:.6f} s'.format(func.__name__, time_spend))
        return result
    return func_wrapper




