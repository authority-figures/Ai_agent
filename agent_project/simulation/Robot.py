import pybullet as p
import numpy as np
from ikpy.chain import Chain
from utils import *
import xml.etree.ElementTree as ET
import sys,os
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
import time

class Robot:


    def __init__(self, id_client):
        self.id_client = id_client

        self.id_robot = None
        self.num_all_joints = None
        self.ids_all_joints = None
        self.num_avail_joints = None
        self.ids_avail_joints = None
        self.link_pairs = []
        self.f_print = False
        self.info_joints = []
        self.id_end_effector = None
        self.info_end_effector = None
        self.ids_draw = []
        self.states_joints = None
        self.baseFramePosition = None
        self.baseLinkPosition = [0,0,0]
        self.inverse_mode='world_sys'

        self.debug_lines:dict[dict[str]]={}
        self.line_x_axis = None
        self.line_y_axis = None
        self.line_z_axis = None

    @staticmethod
    def quat_to_rot_matrix(quaternion,type='xyzw'):
        """
        将四元数转换为旋转矩阵。
        """
        q = quaternion
        if type=='wxyz':
            pass
        elif type == 'xyzw':
            q = (quaternion[3],quaternion[0],quaternion[1], quaternion[2])


        return np.array(
            [[1 - 2 * q[2] ** 2 - 2 * q[3] ** 2, 2 * q[1] * q[2] - 2 * q[3] * q[0], 2 * q[1] * q[3] + 2 * q[2] * q[0]],
             [2 * q[1] * q[2] + 2 * q[3] * q[0], 1 - 2 * q[1] ** 2 - 2 * q[3] ** 2, 2 * q[2] * q[3] - 2 * q[1] * q[0]],
             [2 * q[1] * q[3] - 2 * q[2] * q[0], 2 * q[2] * q[3] + 2 * q[1] * q[0], 1 - 2 * q[1] ** 2 - 2 * q[2] ** 2]])

    @staticmethod
    def get_com_in_link_frame(body_id, link_id,baseFramePosition=[0,0,0], **kwargs,):
        """
        获取link质心在其本体坐标系下的坐标。

        参数:
        - body_id: 机器人或物体的body ID。
        - link_id: link的ID。

        返回:
        - 质心在本体坐标系下的坐标。
        """
        # 获取link的状态，包括质心的世界坐标位置和姿态，以及link frame的位置和姿态
        if link_id == -1:
            # 对于基础部分，使用getBasePositionAndOrientation获取位置和姿态
            base_position, base_orientation = p.getBasePositionAndOrientation(body_id, **kwargs)
            # 基础部分的质心位置即为基础部分的世界坐标位置
            com_world_position = base_position
            # 基础部分的frame位置和姿态即为基础部分本身的位置和姿态
            link_frame_position = baseFramePosition
            link_frame_orientation = base_orientation
        else:

            link_state = p.getLinkState(body_id, link_id,**kwargs)
            com_world_position = link_state[0]  # 质心的世界坐标位置
            link_frame_position = link_state[4]  # Link frame的世界坐标位置
            link_frame_orientation = link_state[5]  # Link frame的世界坐标方向（四元数）

        # 将四元数转换为旋转矩阵
        rot_matrix = Robot.quat_to_rot_matrix(link_frame_orientation)

        # 计算质心相对于link frame的世界坐标位置的向量
        com_vector_world = np.array(com_world_position) - np.array(link_frame_position)

        # 使用旋转矩阵的逆（因为我们是从世界坐标转到本体坐标）来变换这个向量
        rot_matrix_inv = np.linalg.inv(rot_matrix)
        com_vector_local = np.dot(rot_matrix_inv, com_vector_world)


        return com_vector_local.tolist()


    def get_position_relative_to_link(self, bodyA_id, bodyB_id, linkA_id, linkB_id):
        """
        获取一个link相对于另一个link的位置和姿态。
        获取A在B下的表示

        参数:
        - body_id: 机器人的ID。
        - linkA_id: 目标link的ID（例如主轴末端）。
        - linkB_id: 参考link的ID（例如C轴）。

        返回:
        - 相对位置和相对姿态（作为四元数）。
        """
        # 获取两个link的世界坐标系下的位置和姿态
        stateA = p.getLinkState(bodyA_id, linkA_id, physicsClientId=self.id_client)
        stateB = p.getLinkState(bodyB_id, linkB_id, physicsClientId=self.id_client)

        posA, oriA = stateA[4], stateA[5]  # 位置和姿态（四元数）
        posB, oriB = stateB[4], stateB[5]  # 位置和姿态（四元数）

        # 将四元数转换为旋转矩阵
        matB = p.getMatrixFromQuaternion(oriB)
        matB = np.array(matB).reshape(3, 3)

        # 计算相对位置：将posA转换为numpy数组，然后减去posB
        relative_pos = np.array(posA) - np.array(posB)

        # 使用C轴的逆旋转矩阵来转换主轴末端的位置到C轴坐标系下
        inv_matB = np.linalg.inv(matB)
        relative_pos_in_B = np.dot(inv_matB, relative_pos)

        # 对于姿态，可以通过相似的方式计算四元数之间的相对姿态，需要使用四元数的乘法和逆

        return relative_pos_in_B.tolist(), oriA  # 返回相对位置和原始姿态


    def show_link_sys(self, linkIndex=0, lifetime=0, type=0,name=None):

        if linkIndex == -1:
            # 对于基础部分，使用getBasePositionAndOrientation获取位置和姿态
            endEffectorState = p.getBasePositionAndOrientation(self.id_robot)
            if type==0:
                # 返回的是link质心的坐标系
                endEffectorPos, endEffectorOri = endEffectorState[0], endEffectorState[1]
            else:
                endEffectorPos, endEffectorOri = endEffectorState[0], endEffectorState[1]   # 质心坐标系在世界坐标系下的表示
                # 将质心偏移向量转换到世界坐标系
                # 首先，需要将四元数转换为旋转矩阵
                rot_matrix = np.array(p.getMatrixFromQuaternion(endEffectorOri)).reshape(3, 3)

                # 应用旋转矩阵到偏移向量
                offset_world = rot_matrix.dot(self.baseFramePosition)

                # 计算 link 原点的世界坐标位置
                endEffectorPos = endEffectorPos - offset_world


        else:
            endEffectorState = p.getLinkState(self.id_robot, linkIndex)
        # endEffectorPos = endEffectorState[0]
        # 假设endEffectorPos和endEffectorOri是你从getLinkState获取的位置和方向
            if type == 0:
                # 返回的是link质心的坐标系
                endEffectorPos, endEffectorOri = endEffectorState[0], endEffectorState[1]
            else:
                endEffectorPos, endEffectorOri = endEffectorState[4], endEffectorState[5]
        # 计算旋转矩阵
        rot_matrix = p.getMatrixFromQuaternion(endEffectorOri)
        rot_matrix = np.array(rot_matrix).reshape(3, 3)

        # 定义轴的长度
        axis_length = 0.1

        # 绘制X轴（红色）
        x_axis = rot_matrix @ np.array([axis_length, 0, 0])
        y_axis = rot_matrix @ np.array([0, axis_length, 0])
        z_axis = rot_matrix @ np.array([0, 0, axis_length])

        if name is not None:

            if not self.debug_lines.get(name):
                self.debug_lines[name] = {}

            self.debug_lines[name]['line_x_axis'] = p.addUserDebugLine(endEffectorPos, endEffectorPos + x_axis, lineColorRGB=[1, 0, 0], lineWidth=2,
                               lifeTime=lifetime if lifetime >= 0 else 0,
                               replaceItemUniqueId=self.debug_lines[name]['line_x_axis'] if (self.debug_lines and
                                                                                             self.debug_lines.get(name) and
                                                                                             self.debug_lines.get(name).get('line_x_axis') and
                                                                                             lifetime==-1) else -1,
                               )
            # 绘制Y轴（绿色）

            self.debug_lines[name]['line_y_axis'] = p.addUserDebugLine(endEffectorPos, endEffectorPos + y_axis,
                                                                       lineColorRGB=[0, 1, 0], lineWidth=2,
                                                                       lifeTime=lifetime if lifetime >= 0 else 0,
                                                                       replaceItemUniqueId=self.debug_lines[name][
                                                                           'line_y_axis'] if (self.debug_lines and
                                                                                   self.debug_lines.get(name) and
                                                                                   self.debug_lines.get(name).get(
                                                                                       'line_y_axis') and
                                                                                   lifetime == -1) else -1,
                                                                       )

            # 绘制Z轴（蓝色）

            self.debug_lines[name]['line_z_axis'] = p.addUserDebugLine(endEffectorPos, endEffectorPos + z_axis,
                                                                       lineColorRGB=[0, 0, 1], lineWidth=2,
                                                                       lifeTime=lifetime if lifetime >= 0 else 0,
                                                                       replaceItemUniqueId=self.debug_lines[name][
                                                                           'line_z_axis'] if (self.debug_lines and
                                                                                   self.debug_lines.get(name) and
                                                                                   self.debug_lines.get(name).get(
                                                                                       'line_z_axis') and
                                                                                   lifetime == -1) else -1,
                                                                       )
        else:
            self.line_x_axis = p.addUserDebugLine(endEffectorPos, endEffectorPos + x_axis, lineColorRGB=[1, 0, 0],
                                                  lineWidth=2,
                                                  lifeTime=lifetime if lifetime >= 0 else 0,
                                                  replaceItemUniqueId=self.line_x_axis if (
                                                              self.line_x_axis is not None and lifetime == -1) else -1,
                                                  )
            # 绘制Y轴（绿色）
            self.line_y_axis = p.addUserDebugLine(endEffectorPos, endEffectorPos + y_axis, lineColorRGB=[0, 1, 0],
                                                  lineWidth=2,
                                                  lifeTime=lifetime if lifetime >= 0 else 0,
                                                  replaceItemUniqueId=self.line_y_axis if (
                                                              self.line_y_axis is not None and lifetime == -1) else -1,
                                                  )

            # 绘制Z轴（蓝色）
            self.line_z_axis = p.addUserDebugLine(endEffectorPos, endEffectorPos + z_axis, lineColorRGB=[0, 0, 1],
                                                  lineWidth=2,
                                                  lifeTime=lifetime if lifetime >= 0 else 0,
                                                  replaceItemUniqueId=self.line_z_axis if (
                                                              self.line_z_axis is not None and lifetime == -1) else -1,
                                                  )
        return np.array(endEffectorPos), np.array(endEffectorOri)
        pass

    def _is_not_fixed(self, id_joint):
        return p.getJointInfo(self.id_robot, id_joint, physicsClientId=self.id_client)[2] != p.JOINT_FIXED

    def load_urdf(self, *args, **kwargs):
        '''

        :param args: fileName
        :param kwargs:  basePosition=None, baseOrientation=None, useMaximalCoordinates=0, useFixedBase=0, flags=0, globalScaling=1.0, physicsClientId=0
        :return:
        '''
        id_p = self.id_client
        # with disable_b3Printf():
        # # with HideOutput():
        #     self.id_robot = p.loadURDF(*args, **kwargs, physicsClientId=id_p)
        self.id_robot = p.loadURDF(*args, **kwargs, physicsClientId=id_p)

        # 导入时，记录urdf基本信息
        self.get_robot_info()

        # self.collision_self_exclude_parent()  # 过滤碰撞对


        self.baseFramePosition = self.get_link_inertial_origin(kwargs['fileName'],'base_link')
        self.baseLinkPosition = kwargs['basePosition']
        self.robot_chain = Chain.from_urdf_file(kwargs['fileName'])
        # 设置 active_links_mask，将固定连杆设为 False
        active_links_mask = [link.joint_type != 'fixed' for link in self.robot_chain.links]
        self.robot_chain.active_links_mask = active_links_mask

    def init_by_id(self, id_robot):
        self.id_robot = id_robot
        # 导入时，记录urdf基本信息
        self.get_robot_info()

        self.collision_self_exclude_parent()



    def get_link_inertial_origin(self, urdf_file, link_name, inverse=False):
        '''
        读取质心与原点的偏置
        :param urdf_file:
        :param link_name:
        :param inverse:
        :return:
        '''
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # urdf_file = os.path.join(script_dir, 'urdf',urdf_file)
        urdf_file = urdf_file   # 这里不需要路径转换，因为robot和执行脚本在同一个根目录
        tree = ET.parse(urdf_file)
        root = tree.getroot()

        # 获取第一个link元素
        link = root.find('link')
        if link is not None:
            inertial = link.find('inertial')
            if inertial is not None:
                origin = inertial.find('origin')
                if origin is not None:
                    xyz = origin.get('xyz')
                    if xyz:
                        # 根据是否需要反转，返回相应的偏置值
                        return [-float(x) for x in xyz.split()] if inverse else [float(x) for x in xyz.split()]
        return [0,0,0]

    def set_id_end_effector(self, i):
        self.id_end_effector = int(i)

    def set_joint_ranges(self, joint_ranges):
        """
        重新设定所有关节的运动范围。

        :param joint_ranges: 列表，包含每个关节的运动范围 (min, max)。
        """
        # 初始化关节范围字典
        self.dynamic_joint_ranges = {}
        for i in range(self.num_all_joints):
            joint_info = p.getJointInfo(self.id_robot, i)
            self.dynamic_joint_ranges[i] = (joint_info[8], joint_info[9])
        for i in range(self.num_all_joints):
            min_range, max_range = joint_ranges[i]
            if min_range is None or max_range is None:
                continue
            p.changeDynamics(self.id_robot, i, jointLowerLimit=min_range, jointUpperLimit=max_range, jointLimitForce=10000,physicsClientId=self.id_client)
            self.dynamic_joint_ranges[i] = (min_range, max_range)
            print(f"Joint {i} range set to [{min_range}, {max_range}]")

    def get_robot_info(self):
        id_p = self.id_client
        self.num_all_joints = p.getNumJoints(self.id_robot, physicsClientId=id_p)
        self.ids_all_joints = list(range(self.num_all_joints))
        self.id_end_effector = int(self.num_all_joints - 1)  # 默认是最后一个link是末端关节
        self.ids_avail_joints = [j for j in self.ids_all_joints if self._is_not_fixed(j)]
        self.num_avail_joints = len(self.ids_avail_joints)
        print("")
        for i in self.ids_all_joints:
            joint_info = p.getJointInfo(self.id_robot, i, physicsClientId=id_p)
            joint_index = joint_info[0]
            joint_name = joint_info[1].decode('utf-8')  # link名称通常是以字节形式返回的，所以需要解码为字符串
            link_name = joint_info[12].decode('utf-8')  # link名称通常是以字节形式返回的，所以需要解码为字符串
            parent_link_id = joint_info[16]
            self.link_pairs.append([parent_link_id, joint_index])

            lower = joint_info[8]
            upper = joint_info[9]
            id_type = joint_info[2]
            name_ext = ""
            if id_type == 0:
                name_ext = "(rad)"
                if upper < lower:
                    # 持续旋转轴暂时设置一个较大的范围
                    lower = -1e3
                    upper = 1e3
            elif id_type == 1:
                name_ext = "(m)"
            elif id_type == 4:
                # 固定轴
                lower = 0
                upper = 0
            else:
                raise TypeError("暂时只支持JOINT_REVOLUTE, JOINT_PRISMATIC, JOINT_FIXED的滑块！")

            self.info_joints.append([str(joint_name) + name_ext, lower, upper])  #
            if self.f_print:
                print(f"Joint Index: {str(joint_index).ljust(2)}, Joint Name: {joint_name.ljust(10)}, "
                      f"Link Name: {link_name.ljust(20)}, Parent Link ID: {parent_link_id}")
        print("")

    def collision_self_exclude_parent(self):
        for i in self.ids_all_joints:
            p.setCollisionFilterPair(self.id_robot, self.id_robot, i, i, enableCollision=0,
                                     physicsClientId=self.id_client)
        for pair in self.link_pairs:
            p.setCollisionFilterPair(self.id_robot, self.id_robot, pair[0], pair[1], enableCollision=0,
                                     physicsClientId=self.id_client)
            p.setCollisionFilterPair(self.id_robot, self.id_robot, pair[1], pair[0], enableCollision=0,
                                     physicsClientId=self.id_client)

    def get_joints_states(self, mode=0):
        states = p.getJointStates(self.id_robot, self.ids_avail_joints, physicsClientId=self.id_client)
        if mode == 0:
            # 只输出位置
            self.states_joints = [val[0] for val in states]
        else:
            self.states_joints = states
        return self.states_joints

    def get_end_effector_info(self):
        link_state = p.getLinkState(self.id_robot, self.id_end_effector, computeForwardKinematics=1,
                                    physicsClientId=self.id_client)
        pos = link_state[4]
        ori = link_state[5]
        self.info_end_effector = [pos, ori]
        return self.info_end_effector

    def set_joints_states(self, vals):
        for i, val in zip(self.ids_avail_joints, vals):
            p.resetJointState(self.id_robot, i, val, physicsClientId=self.id_client)

    def draw_joint_coordinate(self, ids_joint=None, f_update=True):
        if f_update :   # and p.isConnected(physicsClientId=self.id_client)
            for i in self.ids_draw :
                p.removeUserDebugItem(i, physicsClientId=self.id_client)
            self.ids_draw = []
        if ids_joint is None:
            ids_joint = self.ids_avail_joints
        for i in ids_joint:
            link_state = p.getLinkState(self.id_robot, i, physicsClientId=self.id_client)
            joint_pos = link_state[0]
            joint_ori = link_state[1]
            rot_matrix = np.array(p.getMatrixFromQuaternion(joint_ori, physicsClientId=self.id_client)).reshape(3, 3)
            axis_length = 0.1
            x = rot_matrix @ np.array([axis_length, 0, 0])
            y = rot_matrix @ np.array([0, axis_length, 0])
            z = rot_matrix @ np.array([0, 0, axis_length])
            # X轴（红色）
            id1 = p.addUserDebugLine(joint_pos, joint_pos+x, [1, 0, 0], lineWidth=2, physicsClientId=self.id_client)
            # Y轴（绿色）
            id2 = p.addUserDebugLine(joint_pos, joint_pos+y, [0, 1, 0], lineWidth=2, physicsClientId=self.id_client)
            # Z轴（蓝色）
            id3 = p.addUserDebugLine(joint_pos, joint_pos+z, [0, 0, 1], lineWidth=2, physicsClientId=self.id_client)
            self.ids_draw.extend([id1, id2, id3])

    def get_state_from_ik(self, pos, ori, damping=(0.1,), start=None, currentPosition=None,maxNumIteration=100):

        current_joint_positions = self.get_joints_states()
        if self.inverse_mode=='world_sys':


            if start is not None:
                self.set_joints_states(start)

            if currentPosition is None:
                data = p.getJointStates(self.id_robot, self.ids_avail_joints, physicsClientId=self.id_client)
                currentPosition = [info[0] for info in data]
            lower_limits = [info[1] for info in [self.info_joints[j] for j in self.ids_avail_joints]]
            upper_limits = [info[2] for info in [self.info_joints[j] for j in self.ids_avail_joints]]
            joint_ranges = [v1 - v2 for v1, v2 in zip(upper_limits, lower_limits)]

            if len(damping) < self.num_avail_joints:
                damping = [damping[0]] * self.num_avail_joints

            joints_value = p.calculateInverseKinematics(self.id_robot, self.id_end_effector,
                                                        targetPosition=pos,
                                                        targetOrientation=ori,
                                                        upperLimits=upper_limits, lowerLimits=lower_limits,
                                                        jointRanges=joint_ranges,
                                                        maxNumIterations=maxNumIteration,
                                                        jointDamping=damping,
                                                        # currentPositions=currentPosition,
                                                        )
            self.set_joints_states(current_joint_positions)
        else:

            if ori is not None:
                # 将四元数转换为旋转矩阵
                rotation = R.from_quat(ori)
                rotation_matrix = rotation.as_matrix()

                # 构建 4x4 变换矩阵
                transform_matrix = np.eye(4)
                transform_matrix[:3, :3] = rotation_matrix
                transform_matrix[:3, 3] = pos
                if start is not None:

                    start.insert(0, 0)
                    initial_position = start
                else:
                    start = current_joint_positions
                    start.insert(0, 0)
                    initial_position = start
                joints_value = self.robot_chain.inverse_kinematics_frame(
                    target=transform_matrix,
                    initial_position=initial_position,
                    orientation_mode='all'
                )[1:]
            else:
                # 构建 4x4 变换矩阵
                transform_matrix = np.eye(4)
                transform_matrix[:3, 3] = pos
                if start is not None:
                    start.insert(0, 0)
                    initial_position = start
                else:
                    start = current_joint_positions
                    start.insert(0, 0)
                    initial_position = start
                joints_value = self.robot_chain.inverse_kinematics_frame(
                    target=transform_matrix,
                    initial_position=initial_position,
                )[1:]



        return joints_value



    def run_joints_lists(self,joints_lists,robot_id, sleep_time=0.05, KP=0.1, KD=0.3,targetVelocity=0.2):
        num_joints = p.getNumJoints(robot_id)
        # 遍历所有给定的关节角列表
        for joints in joints_lists:
            # 检查关节角列表的长度与机器人关节数是否匹配
            if len(joints) != num_joints:
                raise ValueError("Length of joints list does not match the number of joints in the robot.")
        for joints in joints_lists:
            for i, joint_position in enumerate(joints):
                p.setJointMotorControl2(robot_id, i, p.POSITION_CONTROL, targetPosition=joint_position,
                                        targetVelocity=0.0,
                                        positionGain=KP,  # KP
                                        velocityGain=KD,  # KD
                                        force=1000,
                                        )
                # 确保每次更新都伴随物理计算

            p.stepSimulation()
            # 控制更新频率
            time.sleep(sleep_time)


        pass

    @staticmethod
    def linear_interpolation(q1, q2, num_intermediate_points):
        """

        :param q1: 参数空间点
        :param q2: 参数空间点
        :param num_intermediate_points: 插值点数
        :return:
        """
        interpolated_q_list = []
        for t in np.linspace(0, 1, num_intermediate_points):
            # interpolated_q = tuple([(1 - t) * q1[i] +
            #                         t * q2[i] for i in range(len(q1))])
            interpolated_q = tuple([(1 - t) * q1[i] + t * q2[i] if q1[i] is not None and q2[i] is not None else q1[i] if
                q2[i] is None else q2[i] for i in range(len(q1))])
            interpolated_q_list.append(interpolated_q)

        return interpolated_q_list
    @staticmethod
    def distance(q1, q2):
        # Calculate distance between two configurations
        # return np.linalg.norm(np.array(q1) - np.array(q2))
        return sum((a - b) ** 2 for a, b in zip(q1, q2) if a is not None and b is not None) ** 0.5

    def interpolation_path(self, joint_value_list, scale=1,add_more_end=0,id_index=None):
        """

        :param joint_value_list: 待插补参数点集
        :param scale: 插补缩放因子
        id_index: 指定列表中某一列为索引
        :return: 插补后参数点集
        """
        coefficient = 0.1/scale
        interpolated_lists = []
        for i in range(len(joint_value_list)-1):


            q1, q2 = joint_value_list[i], joint_value_list[i+1]
            if id_index is not None:
                # 表示索引的那一列不参与距离计算
                q1_d = np.delete(q1, id_index)
                q2_d = np.delete(q2, id_index)
                d = self.distance(q1_d, q2_d)
            else:
                d = self.distance(q1, q2)
            num = int(d / coefficient)  # 插补点数
            interpolated_list = self.linear_interpolation(q1, q2, num)[1:-1]    # 去掉q1，q2


            interpolated_lists.append(q1)
            interpolated_lists.extend(interpolated_list)
        interpolated_lists.append(joint_value_list[-1])
        for _ in range(add_more_end):
            interpolated_lists.append(joint_value_list[-1])

        return interpolated_lists
        pass

    def calc_path_joints(self,current_pos,current_ori,target_pos,target_ori,start=None,scale=1):
        joint_lists = []
        if not current_pos:
            current_pos = list(p.getLinkState(self.id_robot, self.id_end_effector)[4])
            current_ori = list(p.getLinkState(self.id_robot, self.id_end_effector)[5])
        joint_list1 = list(self.get_state_from_ik(current_pos, current_ori,start=None))
        joint_list2= list(self.get_state_from_ik(target_pos,target_ori,start=start))
        joint_lists.append(joint_list1)
        joint_lists.append(joint_list2)
        # interpolation_paths = self.interpolation_path(joint_lists,scale=scale)
        return joint_lists
        pass

    def has_reached_target(self,target_values, tolerance):

        current_positions = [p.getJointState(self.id_robot, i)[0] for i in range(len(target_values))]
        if_return = all(not target or (abs(current - target) < tolerance) for current, target in
                        zip(current_positions, target_values))
        return if_return

    def calculate_ee_origin_from_target(self,target_point_world,target_ori_world, point_in_ee_frame, ori_in_ee_frame=[0,0,0,1],inverse=False,ee_origin_world=None,ee_orientation_world=None):
        """
        计算末端执行器原点在世界坐标系中的位置和姿态。

        参数:
        target_point_world (array-like): 世界坐标系下的目标点 [x, y, z]
        target_ori_world (array-like): 世界坐标系下的目标点姿态 (四元数 [x, y, z, w])
        point_in_ee_frame (array-like): 末端执行器坐标系下的指定点 [x, y, z]
        ori_in_ee_frame (array-like): 指定点在末端执行器坐标系下的姿态 (四元数 [x, y, z, w])

        返回:
        tuple: 世界坐标系下末端执行器的原点位置和姿态 ([x, y, z], [x, y, z, w])
        """
        # 将四元数转换为旋转矩阵
        if inverse==False:
            target_rot = R.from_quat(target_ori_world)
            ee_rot = R.from_quat(ori_in_ee_frame)

            # 计算末端执行器的姿态 (四元数)
            ee_orientation_world = (target_rot * ee_rot.inv()).as_quat()

            # 计算末端执行器原点在世界坐标系中的位置
            ee_origin_world = target_point_world - target_rot.apply(point_in_ee_frame)
            return ee_origin_world, ee_orientation_world
        else:
            # 将四元数转换为旋转矩阵
            ee_rot = R.from_quat(ee_orientation_world)
            point_rot = R.from_quat(ori_in_ee_frame)

            # 计算目标点的姿态 (四元数)
            target_rot = ee_rot * point_rot
            target_ori_world = target_rot.as_quat()

            # 计算目标点在世界坐标系中的位置
            target_point_world = ee_origin_world + ee_rot.apply(point_in_ee_frame)
            return target_point_world, target_ori_world



    @staticmethod
    def TAB_with_AinW_and_BinW(pos_A, ori_A, pos_B, ori_B):
        """
        计算 A 在 B 坐标系下的位置和姿态。

        参数:
        - pos_A: A 在 W 下的位置 (3 元素列表或数组)
        - ori_A: A 在 W 下的姿态 (四元数, 4 元素列表或数组)
        - pos_B: B 在 W 下的位置 (3 元素列表或数组)
        - ori_B: B 在 W 下的姿态 (四元数, 4 元素列表或数组)

        返回:
        - T_AB: A 在 B 下的 4x4 变换矩阵
        """
        # 计算 T_AW 矩阵
        rot_A = R.from_quat(ori_A).as_matrix()
        T_AW = np.eye(4)
        T_AW[:3, :3] = rot_A
        T_AW[:3, 3] = pos_A

        # 计算 T_BW 矩阵
        rot_B = R.from_quat(ori_B).as_matrix()
        T_BW = np.eye(4)
        T_BW[:3, :3] = rot_B
        T_BW[:3, 3] = pos_B

        # 计算 T_WB 矩阵 (T_BW 的逆)
        T_WB = np.linalg.inv(T_BW)

        # 计算 T_AB 矩阵
        T_AB = np.dot(T_WB, T_AW)

        return T_AB


    def update(self, mode=0):
        if mode == 0:
            self.get_joints_states()
            self.get_end_effector_info()
        elif mode == 1:
            self.get_joints_states()
            self.get_end_effector_info()
        elif mode == 2:
            self.get_joints_states()
            self.get_end_effector_info()
            self.draw_joint_coordinate(ids_joint=[self.id_end_effector])
        elif mode == 3:
            self.get_joints_states()
            self.get_end_effector_info()
            self.draw_joint_coordinate()
        elif mode == -1:
            # do nothing
            pass
