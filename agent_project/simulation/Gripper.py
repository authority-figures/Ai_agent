import time

import pybullet as p
import numpy as np

import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from Robot import Robot
# from Robot.Robot import Robot
import math
from scipy.spatial.transform import Rotation as R


class Gripper(Robot):
    def __init__(self, id_client):
        super(Gripper,self).__init__(id_client)
        self.all_links_info = {}
        self.dynamic_joint_ranges = {}
        self.constraint_list = []
        self.left_ori_joint = None
        self.right_ori_joint = None
        self.left_end_link = None
        self.right_end_link = None
        self.gripper_info = {}


        self.new_joint_ranges = [(0,0.9),(None,None),(None,None),(None,None),(-0.9,0),
                                 (None,None),(None,None),(None,None),(None,None),(None,None),]

        # self.new_joint_ranges = [(None, None), (None, None), (None, None), (None, None), (None, None),
        #                          (None, None), (None, None), (None, None), (None, None), (None, None), ]

    def set_joint_ranges(self, joint_ranges):
        """
        重新设定所有关节的运动范围。

        :param joint_ranges: 列表，包含每个关节的运动范围 (min, max)。
        """
        # 初始化关节范围字典
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

    def lock_joint(self, joint_index,lock_force=1000):
        """
        锁死某一关节。

        :param joint_index: 需要锁死的关节索引。
        """
        p.setJointMotorControl2(self.id_robot, joint_index, p.POSITION_CONTROL, targetPosition=0, force=lock_force)

    def set_spring_force(self, joint_index, k=100):
        """
        为某一关节提供一个弹簧弹力，弹力大小与角位移成正比。

        :param joint_index: 需要施加弹簧弹力的关节索引。
        :param k: 弹簧刚度系数。
        """
        # 获取当前关节位置
        joint_state = p.getJointState(self.id_robot, joint_index)
        current_position = joint_state[0]

        # 计算弹簧力（弹力大小与角位移成正比）
        spring_force = -k * current_position

        # 施加弹簧力
        p.setJointMotorControl2(self.id_robot, joint_index, p.TORQUE_CONTROL, force=spring_force)
        # p.setJointMotorControl2(self.id_robot, joint_index, p.VELOCITY_CONTROL, targetVelocity=current_position*20)

    def create_spring_constraint(self):

        pass



    def get_link_info(self, ifshow=True):
        num_joints = p.getNumJoints(self.id_robot)

        # 遍历所有关节
        for joint_index in range(num_joints):
            # 获取关节信息
            joint_info = p.getJointInfo(self.id_robot, joint_index)

            # 获取关联的link名称和ID
            link_name = joint_info[12].decode('UTF-8')  # link名称
            link_id = joint_index  # link ID通常和关节索引相同

            # 存储信息
            self.all_links_info[link_id] = link_name

        # 打印所有link信息
        if ifshow:
            print("+" * 50)
            for link_id, link_name in self.all_links_info.items():
                print(f"Link ID: {link_id}, Link Name: {link_name}")
            print("-" * 50)
        pass

    # def show_link_sys(self, linkIndex=0, lifetime=0, type=0):
    #
    #     if linkIndex == -1:
    #         # 对于基础部分，使用getBasePositionAndOrientation获取位置和姿态
    #         endEffectorState = p.getBasePositionAndOrientation(self.id_robot)
    #
    #     else:
    #         endEffectorState = p.getLinkState(self.id_robot, linkIndex)
    #     # endEffectorPos = endEffectorState[0]
    #     # 假设endEffectorPos和endEffectorOri是你从getLinkState获取的位置和方向
    #     if type == 0:
    #         # 返回的是link质心的坐标系
    #         endEffectorPos, endEffectorOri = endEffectorState[0], endEffectorState[1]
    #     else:
    #         if linkIndex == -1:
    #             endEffectorPos, endEffectorOri = [0,0,0], endEffectorState[1]
    #         else:
    #             endEffectorPos, endEffectorOri = endEffectorState[4], endEffectorState[5]
    #     # 计算旋转矩阵
    #     rot_matrix = p.getMatrixFromQuaternion(endEffectorOri)
    #     rot_matrix = np.array(rot_matrix).reshape(3, 3)
    #
    #     # 定义轴的长度
    #     axis_length = 0.1
    #
    #     # 绘制X轴（红色）
    #     x_axis = rot_matrix @ np.array([axis_length, 0, 0])
    #     p.addUserDebugLine(endEffectorPos, endEffectorPos + x_axis, lineColorRGB=[1, 0, 0], lineWidth=2,
    #                        lifeTime=lifetime)
    #
    #     # 绘制Y轴（绿色）
    #     y_axis = rot_matrix @ np.array([0, axis_length, 0])
    #     p.addUserDebugLine(endEffectorPos, endEffectorPos + y_axis, lineColorRGB=[0, 1, 0], lineWidth=2,
    #                        lifeTime=lifetime)
    #
    #     # 绘制Z轴（蓝色）
    #     z_axis = rot_matrix @ np.array([0, 0, axis_length])
    #     p.addUserDebugLine(endEffectorPos, endEffectorPos + z_axis, lineColorRGB=[0, 0, 1], lineWidth=2,
    #                        lifeTime=lifetime)
    #     return endEffectorPos,endEffectorOri
    #     pass


    def transform_A2B(self, position_A_in_B, orientation_A_in_B, postion_in_A=np.array([0., 0., 0.]), orientation_in_A=np.array([0., 0., 0., 1.]), com_in_link=None):
        """
            将物体在连杆本体坐标系下的位姿转换为世界坐标系下的位姿。

            :param position_A_in_B: 连杆在世界坐标系中的位置 [x, y, z]
            :param orientation_A_in_B: 连杆在世界坐标系中的方向（四元数） [x, y, z, w]
            :param postion_in_A: 物体在连杆坐标系下的局部位置 [x, y, z]
            :param orientation_in_A: 物体在连杆坐标系下的局部方向（四元数） [x, y, z, w]
            :return: 物体在世界坐标系下的位置和方向（四元数）
            """
        # if com_in_link is not None:
        #     local_position = np.array(local_position) - np.array(com_in_link)

        # 将连杆的四元数转换为旋转矩阵
        link_world_rot_matrix = np.array(p.getMatrixFromQuaternion(orientation_A_in_B)).reshape(3, 3)

        # 将局部位置转换为世界坐标系中的位置
        world_position = np.dot(link_world_rot_matrix, postion_in_A) + position_A_in_B

        # 将局部方向（四元数）转换为旋转矩阵
        local_rot_matrix = np.array(p.getMatrixFromQuaternion(orientation_in_A)).reshape(3, 3)

        # 计算物体在世界坐标系中的旋转矩阵
        world_rot_matrix = np.dot(link_world_rot_matrix, local_rot_matrix)

        # 将世界旋转矩阵转换为四元数
        world_orientation = p.getQuaternionFromEuler(R.from_matrix(world_rot_matrix).as_euler('xyz'))

        return world_position, world_orientation
        pass

    def draw_pos(self,joint_pos, joint_ori=[0,0,0,1], life_time=0.2):
        rot_matrix = np.array(p.getMatrixFromQuaternion(joint_ori, physicsClientId=0)).reshape(3, 3)
        axis_length = 0.1
        x = rot_matrix @ np.array([axis_length, 0, 0])
        y = rot_matrix @ np.array([0, axis_length, 0])
        z = rot_matrix @ np.array([0, 0, axis_length])
        # X轴（红色）
        id1 = p.addUserDebugLine(joint_pos, joint_pos + x, [1, 0, 0], lineWidth=2, physicsClientId=0,
                                 lifeTime=life_time)
        # Y轴（绿色）
        id2 = p.addUserDebugLine(joint_pos, joint_pos + y, [0, 1, 0], lineWidth=2, physicsClientId=0,
                                 lifeTime=life_time)
        # Z轴（蓝色）
        id3 = p.addUserDebugLine(joint_pos, joint_pos + z, [0, 0, 1], lineWidth=2, physicsClientId=0,
                                 lifeTime=life_time)
        pass

    def print_joint_states(self,jointIndex=None,):
        """
        打印当前所有关节的信息。
        """
        print("+" * 50)
        for i in range(self.num_all_joints):
            if jointIndex is not None:
                i=jointIndex
            joint_info = p.getJointInfo(self.id_robot, i)
            joint_state = p.getJointState(self.id_robot, i)
            link_state = p.getLinkState(self.id_robot, i)
            joint_name = joint_info[1].decode('utf-8')
            joint_angle = joint_state[0]
            joint_velocity = joint_state[1]
            joint_reaction_forces = joint_state[2]
            joint_torque = joint_state[3]
            joint_world_position = link_state[4]
            joint_world_orientation = link_state[5]
            if self.dynamic_joint_ranges:
                joint_lower_limit = self.dynamic_joint_ranges[i][0]
                joint_upper_limit = self.dynamic_joint_ranges[i][1]
            else:
                joint_lower_limit,joint_upper_limit = joint_info[8], joint_info[9]
            print(f"Joint {i} - {joint_name}:")
            print(f"  Angle: {joint_angle}")
            print(f"  Dynamic Range: [{joint_lower_limit}, {joint_upper_limit}]")
            print(f"  Velocity: {joint_velocity}")
            print(f"  Reaction Forces: {joint_reaction_forces}")
            print(f"  Torque: {joint_torque}")
            print(f"  World Position: {joint_world_position}")
            print(f"  World Orientation (quaternion): {joint_world_orientation}")
            if jointIndex is not None:
                break

            print()

        print("-" * 50)


    def create_gear_constraints(self,joint_A,joint_B,jointAxis,gearRatio=1,maxForce=None,erp=0.2):
        gear_constraint = p.createConstraint(
            parentBodyUniqueId=self.id_robot,
            parentLinkIndex=joint_A,
            childBodyUniqueId=self.id_robot,
            childLinkIndex=joint_B,
            jointType=p.JOINT_GEAR,
            jointAxis=jointAxis,  # 齿轮的旋转轴
            parentFramePosition=[0, 0, 0],
            childFramePosition=[0, 0, 0],
            parentFrameOrientation=[0, 0, 0, 1],
            childFrameOrientation=[0, 0, 0, 1],
        )

        p.changeConstraint(gear_constraint, gearRatio=gearRatio,erp=erp)    # erp 修正频率
        if maxForce is not None:
            p.changeConstraint(gear_constraint, maxForce=maxForce, )
        self.constraint_list.append(gear_constraint)
        return gear_constraint


    def reset_gear_joints(self,joint_A,joint_B):
        joint_A_angle = p.getJointState(self.id_robot,joint_A)[0]
        p.resetJointState(self.id_robot,joint_B,-joint_A_angle)
        pass

    def set_friction_coefficient(self,friction_coefficient=1.0):
        p.changeDynamics(
            bodyUniqueId=self.id_robot,
            linkIndex=self.left_end_link,
            lateralFriction=friction_coefficient
        )
        p.changeDynamics(
            bodyUniqueId=self.id_robot,
            linkIndex=self.right_end_link,
            lateralFriction=friction_coefficient
        )


        pass


    def create_closed_loop_constraints(self,link_A_id,link_B_id,pos_A,pos_B):
        '''
        创建闭环约束
        :param link_A:
        :param link_B:
        :param pos_A:
        :param pos_B:
        :return:
        '''
        # link_A_state = p.getLinkState(self.id_robot,link_A_id, physicsClientId=self.id_client)
        # point_A_in_world_sys = self.transform_A2B(link_A_state[4],link_A_state[5],pos_A)
        link_A_mass = Robot.get_com_in_link_frame(self.id_robot, link_A_id)
        point_A_in_mass_sys = np.array(pos_A)-np.array(link_A_mass)


        link_B_mass = Robot.get_com_in_link_frame(self.id_robot, link_B_id)
        point_B_in_mass_sys = np.array(pos_B) - np.array(link_B_mass)


        constraint_id = p.createConstraint(parentBodyUniqueId=self.id_robot,
                                           parentLinkIndex=link_A_id,
                                           childBodyUniqueId=self.id_robot,
                                           childLinkIndex=link_B_id,  # 表示连接到工件的基础部分
                                           jointType=p.JOINT_POINT2POINT,   # p.JOINT_POINT2POINT p.JOINT_REVOLUTE
                                           jointAxis=[0, 0, 0],
                                           parentFramePosition=point_A_in_mass_sys,
                                           childFramePosition=point_B_in_mass_sys,
                                           childFrameOrientation=p.getQuaternionFromEuler((0, 0, 0)),
                                           )
        self.constraint_list.append(constraint_id)
        return constraint_id
        pass


    def set_non_driven_velocity_control(self,force=100.):
        p.setJointMotorControl2(self.id_robot, 0, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 1, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 2, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 3, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 4, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 5, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 6, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 7, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 8, p.VELOCITY_CONTROL, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 9, p.VELOCITY_CONTROL, targetVelocity=0, force=force)

        pass


    def add_spring_force(self,link_A_index,link_B_index,pos_A,pos_B, spring_stiffness = 1000, rest_length = 0.02):
        # 定义弹簧的参数
        spring_stiffness = spring_stiffness  # 弹簧刚度系数
        spring_damping = 0.1  # 弹簧阻尼系数
        rest_length = rest_length  # 弹簧的原长


        A_frame_pos, A_frame_ori = p.getLinkState(self.id_robot, link_A_index)[4], p.getLinkState(self.id_robot, link_A_index)[5]
        B_frame_pos, B_frame_ori = p.getLinkState(self.id_robot, link_B_index)[4], p.getLinkState(self.id_robot, link_B_index)[5]
        parent_frame_position = self.transform_A2B(A_frame_pos,A_frame_ori,pos_A)[0]
        child_frame_position = self.transform_A2B(B_frame_pos, B_frame_ori, pos_B)[0]

        # 计算弹簧力
        current_distance = np.linalg.norm(np.array(parent_frame_position) - np.array(child_frame_position))
        spring_force_magnitude = spring_stiffness * (current_distance - rest_length)

        # 计算方向向量
        direction_vector = (np.array(child_frame_position) - np.array(parent_frame_position)) / current_distance

        # 施加弹簧力
        p.applyExternalForce(self.id_robot, link_A_index, forceObj=spring_force_magnitude * direction_vector,
                             posObj=parent_frame_position, flags=p.WORLD_FRAME)
        p.applyExternalForce(self.id_robot, link_B_index, forceObj=-spring_force_magnitude * direction_vector,
                             posObj=child_frame_position, flags=p.WORLD_FRAME)

        return spring_force_magnitude,direction_vector,parent_frame_position,child_frame_position,current_distance

        pass
    
    
    def init_gripper(self,ifshow=False):


        self.left_ori_joint = 0
        self.right_ori_joint = 4
        self.left_end_link = 3
        self.right_end_link = 7
        # 添加闭环约束
        link_l3 = 2  # link_2的索引，根据URDF加载的顺序确定
        link_l4 = 8  # link_2的索引，根据URDF加载的顺序确定
        link_r3 = 6  # link_2的索引，根据URDF加载的顺序确定
        link_r4 = 9  # link_4的索引，根据URDF加载的顺序确定
        # 约束链接点的本体坐标位置
        pivot_in_l4 = np.array([46, 0., 0])
        pivot_in_l3 = np.array([20.5, 0., 0])
        pivot_in_r4 = np.array([46, 0., 0])
        pivot_in_r3 = np.array([20.5, 0., 0])
        # 创建约束
        constraint1 = self.create_closed_loop_constraints(link_l3, link_l4, pivot_in_l3 * 0.001, pivot_in_l4 * 0.001)
        p.changeConstraint(constraint1, maxForce=100000000, physicsClientId=self.id_client)
        constraint2 = self.create_closed_loop_constraints(link_r3, link_r4, pivot_in_r3 * 0.001, pivot_in_r4 * 0.001)
        p.changeConstraint(constraint2, maxForce=100000000, physicsClientId=self.id_client)

        self.get_link_info(ifshow=ifshow)
        # self.set_joint_ranges(self.new_joint_ranges)

        if ifshow:
            self.print_joint_states()
        self.set_non_driven_velocity_control(force=0)

        self.lock_joint(joint_index=1,lock_force=100000)
        self.lock_joint(joint_index=5,lock_force=100000)
        self.create_gear_constraints(0, 4, [0, 1, 0],maxForce=1e9,)
        # self.create_gear_constraints(8, 9, [0, 1, 0], gearRatio=-1,maxForce=1000000)

        self.reset_joint_states()
        for i in range(10):
            p.changeDynamics(self.id_robot, i, mass=1)


        for i in range(self.num_all_joints):
            p.changeDynamics(
                bodyUniqueId=self.id_robot,
                linkIndex=i,
                jointDamping=0.1,
            )

        pass

    def reset_joint_states(self):
        for i in range(self.num_all_joints):
            p.resetJointState(self.id_robot,i,0)
        pass

    def estimate_grip_force(self, object_id):
        if object_id:
            # 获取夹爪与物体之间的接触点
            contacts = p.getContactPoints(bodyA=self.id_robot, bodyB=object_id)
            total_force = 0
            # 累加所有接触点的法向力
            for contact in contacts:
                normal_force = contact[9]  # 法向力
                total_force += normal_force
        else:
            total_force = None
        return total_force

    def get_gripper_info(self, object_id):
        # 字典，用于存储卡爪信息
        self.gripper_info = {}

        # 获取link_l0和link_r0的位置和方向
        state_l0 = p.getLinkState(self.id_robot, self.left_end_link)
        state_r0 = p.getLinkState(self.id_robot, self.right_end_link)

        # 计算两个link原点之间的距离
        position_l0 = state_l0[4]  # 假设index 4是世界坐标位置
        position_r0 = state_r0[4]
        distance = np.linalg.norm(np.array(position_l0) - np.array(position_r0))

        # 获取两个link的摩擦系数
        dynamics_info_l0 = p.getDynamicsInfo(self.id_robot, self.left_ori_joint)
        dynamics_info_r0 = p.getDynamicsInfo(self.id_robot, self.right_ori_joint)
        friction_l0 = dynamics_info_l0[1]  # 假设index 1是摩擦系数
        friction_r0 = dynamics_info_r0[1]

        # 估计夹持力大小
        grip_force = self.estimate_grip_force(object_id=object_id)

        # 将信息存储在字典中
        self.gripper_info['distance_between_grippers'] = distance
        self.gripper_info['friction_coefficient_l0'] = friction_l0
        self.gripper_info['friction_coefficient_r0'] = friction_r0
        self.gripper_info['grip_force'] = grip_force

        return self.gripper_info



    def open(self,mode='useToque',targetVelocity=1.,force=1.,targetPosition=0.2):

        left_effector = self.left_ori_joint
        right_effector = self.right_ori_joint

        if mode=='useVelocity':
            p.setJointMotorControl2(self.id_robot, left_effector , p.VELOCITY_CONTROL, targetVelocity=-targetVelocity,force=force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.VELOCITY_CONTROL, targetVelocity=targetVelocity, force=force)
        elif mode=='useToque':
            p.setJointMotorControl2(self.id_robot, left_effector , p.TORQUE_CONTROL, force=-force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.TORQUE_CONTROL, force=force)

        elif mode=='usePosition':
            p.setJointMotorControl2(self.id_robot, left_effector , p.POSITION_CONTROL,targetPosition=targetPosition,
                                    targetVelocity=0.0,
                                    force=force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.POSITION_CONTROL,targetPosition=-targetPosition,
                                    targetVelocity=0.0,
                                    force=force)
        # self.set_spring_force(joint_index=1, k=1000)
        pass

    def close(self,mode='useToque',targetVelocity=1,force=1.,targetPosition=0.9):

        left_effector = self.left_ori_joint
        right_effector = self.right_ori_joint

        if mode=='useVelocity':
            p.setJointMotorControl2(self.id_robot, left_effector, p.VELOCITY_CONTROL,
                                    targetVelocity=targetVelocity, force=force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.VELOCITY_CONTROL,
                                    targetVelocity=-targetVelocity, force=force)
        elif mode == 'useToque':
            p.setJointMotorControl2(self.id_robot, left_effector, p.TORQUE_CONTROL, force=force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.TORQUE_CONTROL, force=-force)
            # self.set_spring_force(joint_index=1, k=1000)

        elif mode=='usePosition':
            p.setJointMotorControl2(self.id_robot, left_effector, p.POSITION_CONTROL,targetPosition=targetPosition,
                                    targetVelocity=0.0,
                                    # positionGain=0.01,  # KP
                                    # velocityGain=1,  # KD
                                    force=force)
            p.setJointMotorControl2(self.id_robot, right_effector, p.POSITION_CONTROL,targetPosition=-targetPosition,
                                    targetVelocity=0.0,
                                    # positionGain=0.01,  # KP
                                    # velocityGain=1,  # KD
                                    force=force)

        pass




def main1():
    id_client = p.connect(p.GUI)
    gp = Gripper(id_client=id_client)
    file_name = "F:\\sw\\urdf_files\\Gripper\\urdf\\Gripper.urdf"

    # 加载四连杆机构的URDF文件
    gp.load_urdf(fileName=file_name, basePosition=[0, 0, 0], useFixedBase=True)
    robot_id = 0
    # 添加闭环约束
    link_l4 = 3  # link_2的索引，根据URDF加载的顺序确定
    link_r4 = 9  # link_4的索引，根据URDF加载的顺序确定

    # 约束链接点的世界坐标位置
    pivot_in_a = np.array([-17.24, 42.65, 0])

    pivot_in_b = np.array([-7.5, 0., -42.55])


    # 创建点对点约束
    # constraint_id = p.createConstraint(robot_id, link_l4, robot_id, -1, p.JOINT_POINT2POINT, [0, 0, 0], pivot_in_a,
    #                                    pivot_in_b)
    # constraint_id = p.createConstraint(parentBodyUniqueId=robot_id,
    #                                    parentLinkIndex=-1,
    #                                    childBodyUniqueId=robot_id,
    #                                    childLinkIndex=link_l4,  # 表示连接到工件的基础部分
    #                                    jointType=p.JOINT_POINT2POINT,
    #                                    jointAxis=[0, 0, 0],
    #                                    parentFramePosition=[0, 0, 0],
    #                                    childFramePosition=[0, 0, 0],
    #                                    childFrameOrientation=p.getQuaternionFromEuler((0, 0, 0)),
    #                                    )

    constraint1 = gp.create_closed_loop_constraints(-1,3,[-0.0075, 0., -0.04255],[-0.01724, 0.04265, 0])
    p.changeConstraint(constraint1, maxForce=500, physicsClientId=gp.id_client)
    # p.removeConstraint(constraint1)

    gp.set_non_driven_velocity_control()
    gp.set_joint_ranges(gp.new_joint_ranges)
    gp.get_link_info()
    print(p.getBasePositionAndOrientation(robot_id))

    # gp.lock_joint(joint_index=1)
    # gp.set_spring_force(joint_index=1,k=1000)
    # gp.set_spring_force(joint_index=6, k=1000)
    gp.print_joint_states()



    i=0
    while True:
        # gp.set_non_driven_velocity_control()
        gp.show_link_sys(linkIndex=3,lifetime=0.2,type=0)
        gp.show_link_sys(linkIndex=-1, lifetime=0.2, type=0)
        gp.lock_joint(joint_index=1)
        # p.setJointMotorControl2(robot_id,0,p.TORQUE_CONTROL,force=100)
        # p.setJointMotorControl2(robot_id, 5, p.TORQUE_CONTROL, force=100)
        p.setJointMotorControl2(robot_id, 0, p.VELOCITY_CONTROL, targetVelocity=0.5,force=1)

        # gp.set_spring_force(joint_index=1, k=1000)0
        pos_A = gp.get_com_in_link_frame(gp.id_robot,5)
        pos_B = gp.get_com_in_link_frame(gp.id_robot, 6)
        # result = gp.add_spring_force(5,6,pos_A,pos_B,-1000)
        # gp.draw_pos(result[2])
        # gp.draw_pos(result[3])
        # print(result[0],result[4])
        #
        # if i%250==0:
        #     gp.open()
        #     print('open!!!')
        #
        # if i%500==0:
        #     gp.close()
        #     print('close!!!')
        #     i=0

        p.stepSimulation()
        if i%100==0:
            gp.print_joint_states(jointIndex=0)

        # my_machine.show_link_sys(1, 1, type=0)
        time.sleep(1 / 240.)
        i+=1
    pass



def main2():
    id_client = p.connect(p.GUI)
    gp = Gripper(id_client=id_client)
    file_name = "F:\\sw\\urdf_files\\Gripper_1\\urdf\\Gripper_1.urdf"

    # 加载四连杆机构的URDF文件
    gp.load_urdf(fileName=file_name, basePosition=[0, 0, 0], useFixedBase=True)
    robot_id = 0
    # 添加闭环约束
    link_l3 = 2  # link_2的索引，根据URDF加载的顺序确定
    link_l4 = 8  # link_2的索引，根据URDF加载的顺序确定
    link_r3 = 6  # link_2的索引，根据URDF加载的顺序确定
    link_r4 = 9  # link_4的索引，根据URDF加载的顺序确定

    # 约束链接点的本体坐标位置
    pivot_in_l4 = np.array([46, 0., 0])
    pivot_in_l3 = np.array([20.5, 0., 0])
    pivot_in_l_base = np.array([-45.5, 0., -68.47])

    constraint1 = gp.create_closed_loop_constraints(link_l3,link_l4,pivot_in_l3*0.001,pivot_in_l4*0.001)
    p.changeConstraint(constraint1, maxForce=1000, physicsClientId=gp.id_client)
    # p.removeConstraint(constraint1)
    gp.get_link_info()
    print(p.getBasePositionAndOrientation(robot_id))
    gp.set_joint_ranges(gp.new_joint_ranges)

    # gp.set_spring_force(joint_index=1,k=1000)
    # gp.set_spring_force(joint_index=6, k=1000)
    gp.print_joint_states()
    gp.set_non_driven_velocity_control(force=0)
    # while True:
    #     p.stepSimulation()
    #     time.sleep(1/240.)
    #     pass


    i=0

    gp.lock_joint(joint_index=1)
    gp.create_gear_constraints(0,4,[0,1,0])
    while True:

        gp.show_link_sys(linkIndex=link_l4,lifetime=0.2,type=1)
        gp.show_link_sys(linkIndex=link_l3, lifetime=0.2, type=1)
        # gp.lock_joint(joint_index=1)
        # p.setJointMotorControl2(robot_id,0,p.TORQUE_CONTROL,force=100)
        # p.setJointMotorControl2(robot_id, 0, p.TORQUE_CONTROL, force=-100000)
        #
        p.setJointMotorControl2(robot_id, 0, p.VELOCITY_CONTROL, targetVelocity=0.2,force=100)

        # gp.set_spring_force(joint_index=1, k=1000)0
        pos_A = gp.get_com_in_link_frame(gp.id_robot,5)
        pos_B = gp.get_com_in_link_frame(gp.id_robot, 6)
        # result = gp.add_spring_force(5,6,pos_A,pos_B,-1000)
        # gp.draw_pos(result[2])
        # gp.draw_pos(result[3])
        # print(result[0],result[4])

        p.stepSimulation()
        if i%100==0:
            gp.print_joint_states(jointIndex=0)

        # my_machine.show_link_sys(1, 1, type=0)
        time.sleep(1 / 240.)
        i+=1
    pass


def t():
    id_client = p.connect(p.GUI)
    gp = Gripper(id_client=id_client)
    file_name = "F:\\sw\\urdf_files\\Gripper_1\\urdf\\Gripper_1.urdf"
    basePosition=[0,0,0.2]
    baseOrientation = p.getQuaternionFromEuler([1.57, 0, 0])

    # 加载四连杆机构的URDF文件
    gp.load_urdf(fileName=file_name, basePosition=basePosition,baseOrientation=baseOrientation, useFixedBase=True)
    gp.init_gripper()

    # 创建长方体的碰撞形状，设置尺寸
    collision_shape_id = p.createCollisionShape(
        shapeType=p.GEOM_BOX,
        halfExtents=[0.01, 0.01, 0.5]  # x, y, z的半长度，所以总长度分别为20mm, 20mm, 1000mm
    )

    # 创建多体，添加到仿真环境中
    body_id = p.createMultiBody(
        baseMass=1,  # 设置质量
        baseCollisionShapeIndex=collision_shape_id,  # 使用刚刚创建的碰撞形状
        basePosition=[-0.00, 0.11, 0.5],  # 初始位置，基于中心点
        # useFixedBase = True
    )


    # 重力设置，使环境中的物体受重力影响
    p.setGravity(0, 0, -0.1)
    print(Robot.get_com_in_link_frame(gp.id_robot,-1))

    gp.reset_joint_states()

    i=0
    while True:
        # p.setJointMotorControl2(gp.id_robot, 0, p.VELOCITY_CONTROL, targetVelocity=0.2, force=10)
        # p.setJointMotorControl2(gp.id_robot, 0, p.TORQUE_CONTROL, force=0.01)
        if i == 0:
            gp.open('usePosition',targetPosition=0.5,targetVelocity=10,force=10)
            print('open!')

        elif i == 500:
            gp.close(mode='usePosition',targetPosition=0.9,targetVelocity=10,force=10)   # 'useVelocity' 'useToque' 'usePosition'
            print('close!')



        state = p.getLinkState(gp.id_robot, gp.right_end_link)
        gp.draw_pos(state[4],state[5])
        data = gp.get_gripper_info(body_id)
        print(data)
        p.stepSimulation()
        if i % 100 == 0:
            # gp.print_joint_states(jointIndex=0)
            # gp.print_joint_states(jointIndex=gp.right_ori_joint)
            # gp.reset_gear_joints(gp.left_ori_joint,gp.right_ori_joint)
            pass

        # my_machine.show_link_sys(1, 1, type=0)
        time.sleep(1 / 240.)
        i += 1
        if i>1000:
            i=0

        pass


if __name__ == '__main__':
    # main2()
    t()

    pass