import pybullet as p
import numpy as np
from tqdm import tqdm
import sys,os
import time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from my_utils import *
from Robot import Robot
import math
import re
import sympy as sym
import pickle

class Machine(Robot):
    def __init__(self, id_client,c_in_sys0=0.685):
        super(Machine,self).__init__(id_client)

        self.all_links_info = {}
        self.id_workpiece = None
        self.id_tool = None
        self.tool_length = None
        self.spindle_index = None
        self.turntable_index = None
        self.parsed_values = None # 解析后的nc代码
        self.workpiece_pose = [0,0,0]
        self.workpiece_orientation = [0,0,0,1]
        self.C_continue = True
        self.C_in_sys0=c_in_sys0


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


    def get_spindle_and_turntable_index(self):

        '''
        分析link信息，识别出主轴(Spindle)和转台(Table)的ID。
        如果有多个名称都包含"S"或"C"，则以出现次数最多的为准。
        '''
        self.get_link_info(ifshow=False)
        spindle_count = {}
        table_count = {}

        # 遍历所有存储的link信息
        for link_id, link_name in self.all_links_info.items():
            # 统计包含"S"和"C"的link出现次数
            if "S" in link_name:
                spindle_count[link_id] = spindle_count.get(link_id, 0) + 1
            elif "C" in link_name:
                table_count[link_id] = table_count.get(link_id, 0) + 1

        # 确定出现次数最多的主轴ID和转台ID
        self.spindle_index = max(spindle_count, key=spindle_count.get, default=None)
        self.turntable_index = max(table_count, key=table_count.get, default=None)

        pass

    def load_urdf(self, *args, **kwargs):
        super().load_urdf(*args, **kwargs)
        self.get_spindle_and_turntable_index()
        pass

    def init_machine(self,joints=[0, 0, -0.2, 0, 0, 0]):
        self.set_id_end_effector(4)
        self.set_joints_states(joints)
        for i in range(self.num_all_joints):
            p.changeDynamics(
                bodyUniqueId=self.id_robot,
                linkIndex=i,
                jointDamping=0.2,
                mass=10,
                linearDamping=0.5, angularDamping=0.5,
            )
        force = 100000
        mode = p.VELOCITY_CONTROL
        p.setJointMotorControl2(self.id_robot, 0, mode, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 1, mode, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 2, mode, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 3, mode, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 4, mode, targetVelocity=0, force=force)
        p.setJointMotorControl2(self.id_robot, 5, mode, targetVelocity=0, force=force)




    def add_workpiece_to_machine(self, workpiece_urdf_path, position=[0,0,0], orientation=[0,0,0],):
        """
        向机床中添加一个工件，并将其固定在C轴link上。

        参数:s
        - c_axis_link_id: C轴link的ID。
        - workpiece_urdf_path: 工件的URDF文件路径。
        - position: 工件在C轴坐标系中的位置，形式为(x, y, z)。
        - orientation: 工件在C轴坐标系中的姿态，形式为(roll, pitch, yaw)欧拉角。
        """
        self.workpiece_pose = position
        # 将欧拉角转换为四元数
        quaternion = p.getQuaternionFromEuler(orientation)
        self.workpiece_orientation = quaternion

        # 获取C轴的世界坐标系下的位置和姿态
        c_axis_state = p.getLinkState(self.id_robot, self.turntable_index)
        c_axis_pos, c_axis_ori = c_axis_state[4], c_axis_state[5]

        # 将工件的位置和姿态转换为相对于世界坐标系的位置和姿态
        # 注意：这里简化处理，实际情况下可能需要根据C轴的姿态调整工件的姿态
        world_position = [c_axis_pos[0] + position[0], c_axis_pos[1] + position[1], c_axis_pos[2] + position[2]]
        world_orientation = quaternion  # 如果需要，这里可能需要做更复杂的转换

        # 加载工件的URDF文件，并设置其位置和姿态
        self.workpiece = Robot(self.id_client)
        self.workpiece.load_urdf(fileName=workpiece_urdf_path, basePosition=world_position,baseOrientation= world_orientation, useFixedBase=False)
        workpiece_id = self.workpiece.id_robot
        # workpiece_id = p.loadURDF(workpiece_urdf_path, world_position, world_orientation, useFixedBase=False,physicsClientId=self.id_client)

        p.setCollisionFilterPair(self.id_robot, workpiece_id, 1, -1, 0)
        p.setCollisionFilterPair(self.id_robot, workpiece_id, -1, -1, 0)
        p.setCollisionFilterPair(self.id_robot, workpiece_id, 0, -1, 0)
        p.setCollisionFilterPair(self.id_robot, workpiece_id, 5, -1, 0)
        p.setCollisionFilterPair(self.id_robot, workpiece_id, 4, -1, 0)
        # 获取父link的质心坐标
        parentFramePosition = self.get_com_in_link_frame(self.id_robot, self.turntable_index)
        childFramePosition = self.get_com_in_link_frame(workpiece_id, -1,baseFramePosition=world_position)
        childFrameOrientation = invert_quaternion(self.workpiece_orientation)

        # 将工件固定在C轴上
        self.workpiece_constrain = p.createConstraint(parentBodyUniqueId=self.id_robot,
                           parentLinkIndex=self.turntable_index,
                           childBodyUniqueId=workpiece_id,
                           childLinkIndex=-1,  # 表示连接到工件的基础部分
                           jointType=p.JOINT_FIXED,
                           jointAxis=[0, 0, 0],
                           parentFramePosition=[-parentFramePosition[0]+position[0], -parentFramePosition[1]+position[1], -parentFramePosition[2]+position[2]],
                           # childFramePosition=[-position[0], -position[1], -position[2]],
                           childFramePosition=[-childFramePosition[0]+0,-childFramePosition[1]+0,-childFramePosition[2]+0],
                           parentFrameOrientation=c_axis_ori,
                           # childFrameOrientation=p.getQuaternionFromEuler((0, 0, 0)),
                           childFrameOrientation=childFrameOrientation ,
                           )
        self.id_workpiece = workpiece_id
        self.post_processor = self.PostProcessor(self)

        for _ in range(100):
            p.stepSimulation()

        # 获取关节信息




        return workpiece_id





    def add_tool_to_machine(self, tool_urdf_path, tool_length,type=''):
        """
        向机床中添加一个刀具，并将其固定在S轴link上。

        参数:
        - S_axis_link_id: S轴link的ID。
        - workpiece_urdf_path: 工件的URDF文件路径。
        - position: 工件在C轴坐标系中的位置，形式为(x, y, z)。
        - orientation: 工件在C轴坐标系中的姿态，形式为(roll, pitch, yaw)欧拉角。
        """


        # 获取S轴的世界坐标系下的位置和姿态
        S_axis_state = p.getLinkState(self.id_robot, self.spindle_index)
        S_axis_pos, S_axis_ori = S_axis_state[4], S_axis_state[5]

        # 将tool的位置和姿态转换为相对于世界坐标系的位置和姿态
        # 注意：这里简化处理，实际情况下可能需要根据C轴的姿态调整工件的姿态
        world_position = [S_axis_pos[0], S_axis_pos[1] , S_axis_pos[2] - tool_length]


        # 加载工件的URDF文件，并设置其位置和姿态
        tool_id = p.loadURDF(tool_urdf_path, world_position, useFixedBase=False,physicsClientId=self.id_client)

        for i in range(self.num_all_joints+1):
            p.setCollisionFilterPair(self.id_robot, tool_id, i, -1, 0)
        p.setCollisionFilterPair(self.id_robot, tool_id, -1, -1, 0)

        # p.setCollisionFilterPair(self.id_robot, tool_id, 1, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, -1, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, 0, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, 5, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, 4, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, 3, -1, 0)
        # p.setCollisionFilterPair(self.id_robot, tool_id, 2, -1, 0)
        # 获取父link的质心坐标
        parentFramePosition = self.get_com_in_link_frame(self.id_robot, self.spindle_index)
        if type == 'center':
            childLinkIndex = 0
        elif type == 'bottom':
            childLinkIndex = 1
        else:
            childLinkIndex = -1

        # 将工件固定在C轴上
        p.createConstraint(parentBodyUniqueId=self.id_robot,
                           parentLinkIndex=self.spindle_index,
                           childBodyUniqueId=tool_id,
                           childLinkIndex=childLinkIndex,  # 表示连接到工件的基础部分
                           jointType=p.JOINT_FIXED,
                           jointAxis=[0, 0, 0],
                           parentFramePosition=[-parentFramePosition[0], -parentFramePosition[1], -parentFramePosition[2]],
                           childFramePosition=[-0, -0, tool_length],
                           childFrameOrientation=p.getQuaternionFromEuler((0, 0, 0)),
                           )


        # 获取关节信息

        self.tool_length = tool_length
        self.id_tool = tool_id




        return tool_id


    def show_link_sys(self, linkIndex=0, lifetime=0, type=0):
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
        p.addUserDebugLine(endEffectorPos, endEffectorPos + x_axis, lineColorRGB=[1, 0, 0], lineWidth=2,
                           lifeTime=lifetime)

        # 绘制Y轴（绿色）
        y_axis = rot_matrix @ np.array([0, axis_length, 0])
        p.addUserDebugLine(endEffectorPos, endEffectorPos + y_axis, lineColorRGB=[0, 1, 0], lineWidth=2,
                           lifeTime=lifetime)

        # 绘制Z轴（蓝色）
        z_axis = rot_matrix @ np.array([0, 0, axis_length])
        p.addUserDebugLine(endEffectorPos, endEffectorPos + z_axis, lineColorRGB=[0, 0, 1], lineWidth=2,
                           lifeTime=lifetime)
        pass

    # def parse_nc_code(self, file_path):
    #     """
    #     解析NC代码，提取XYZAC的值。
    #
    #     参数:
    #     - file_path: .tp文件的路径。
    #
    #     返回:
    #     - 包含XYZAC值的字典列表。
    #     """
    #     parsed_values = []
    #     with open(file_path, 'r') as file:
    #         nc_code = file.readlines()
    #
    #     for line in tqdm(nc_code, desc="Processing NC codes:解析nc代码为字典格式"):
    #         tokens = line.split()
    #         values = {}
    #         for token in tokens:
    #             try:
    #                 if token.startswith('X'):
    #                     values['X'] = float(token[1:])
    #                 elif token.startswith('Y'):
    #                     values['Y'] = float(token[1:])
    #                 elif token.startswith('Z'):
    #                     values['Z'] = float(token[1:])
    #                 elif token.startswith('A'):
    #                     values['A'] = float(token[1:])
    #                 elif token.startswith('C'):
    #                     values['C'] = float(token[1:])
    #             except ValueError as e:
    #                 print(f"Warning: Unable to parse value from token '{token}': {e}")
    #         if values:  # 如果字典非空
    #             parsed_values.append(values)
    #
    #                 # 使用列表推导式过滤掉空字典
    #         parsed_values = [value for value in parsed_values if value]
    #
    #     self.parsed_values = parsed_values
    #
    #
    #     return parsed_values


    def parse_nc_code(self, file_path):
        """
        解析NC代码，提取N和XYZAC的值。

        参数:
        - file_path: .tp文件的路径。

        返回:
        - 包含N和XYZAC值的字典列表。
        """
        parsed_values = []
        # 正则表达式：
        # ([NXYZAC])：匹配一个字符，这个字符可以是 N, X, Y, Z, A, C 之一，并捕获为第一个分组。
        # ([-+]?\d*\.\d+|\d+)：匹配一个数字，可以是整数或小数，并捕获为第二个分组。
        pattern = re.compile(r"([NXYZAC])([-+]?\d*\.\d+|\d+)")

        with open(file_path, 'r') as file:
            nc_code = file.readlines()

        for line in tqdm(nc_code, desc="Processing NC codes: 解析NC代码为字典格式"):
            matches = pattern.findall(line)
            if matches:
                values = {axis: float(value) if axis != 'N' else int(value) for axis, value in matches}
                parsed_values.append(values)

        self.parsed_values = parsed_values
        return parsed_values





    def get_offset(self, bodyA_id, bodyB_id, linkA_id, linkB_id, tool_length=0.):
        '''

        :param linkA_id: 目标link_id
        :param linkB_id: 参考link_id
        :return: 坐标系的偏置，形式为字典{'X': float, 'Y': float, 'Z': float, 'A': float, 'C': float}
        '''
        # if self.tool_length is not None:
        #     tool_length = self.tool_length
        #
        # offset = {}
        # relative_pos, _ = self.get_position_relative_to_link(bodyA_id, bodyB_id, linkA_id, linkB_id)
        # offset['X'], offset['Y'], offset['Z'], offset['A'], offset['C'] = relative_pos[0], relative_pos[1], relative_pos[2]-tool_length, 0, 0
        # return offset
        # pass

        if self.tool_length is not None:
            tool_length = self.tool_length

        offset = {}
        relative_pos, relative_ori = self.get_position_relative_to_link(bodyA_id, bodyB_id, linkA_id, linkB_id)

        # 将姿态转换为欧拉角
        relative_euler = p.getEulerFromQuaternion(relative_ori)

        # 计算姿态偏差的旋转矩阵
        rot_matrix = p.getMatrixFromQuaternion(relative_ori)
        rot_matrix = np.array(rot_matrix).reshape(3, 3)

        # 计算旋转后的相对位置
        relative_pos_rotated = np.dot(rot_matrix, np.array(relative_pos))

        # 计算偏置，注意Z轴要减去工具长度
        offset['X'] = relative_pos[0]
        offset['Y'] = relative_pos[1]
        offset['Z'] = relative_pos[2] + tool_length
        offset['A'] = relative_euler[0]  # 偏航角
        offset['C'] = relative_euler[2]  # 偏转角

        return offset

    def get_values_with_nc_codes(self, converted_nc_codes=None, spindle_to_workpiece_offset=None):
        """
        根据NC代码和主轴末端到工件坐标系的偏置更新轴位置。

        参数:
        nc_codes: 包含每行NC代码字典的列表。
        spindle_to_workpiece_offset: 主轴末端到工件坐标系的偏置，形式为字典{'X': float, 'Y': float, 'Z': float, 'A': float, 'C': float}。

        返回:
        按照ACXYZ顺序的轴位置列表，缺失的轴值设置为None。
        """
        if converted_nc_codes==None:
            if self.parsed_values==None:
                raise ValueError("NC代码未提供")
            else:
                converted_nc_codes = self.parsed_values


        if spindle_to_workpiece_offset==None:
            # 这里工件的link_id提供的是0，实际上应该为-1，但是-1的信息并不能被getlinkstate读取到，所以这里我修改了urdf文件，添加了一个link0
            # 最好的方法是，在构建joint和link信息列表时，将link-1的信息也添加进去
            self.set_joints_states([0,0,0,0,0,0])   # 添加偏置前回零点
            spindle_to_workpiece_offset = self.get_offset(self.id_robot,self.id_robot, 1,self.spindle_index,)



        joint_values_list = []
        self.post_processor = self.PostProcessor(self)

        converted_nc_codes = self.post_processor.apply_workpiece_offset(converted_nc_codes)

        # 遍历每行NC代码
        for code_line in tqdm(converted_nc_codes, desc="Processing NC codes:应用主轴到转台的偏置"):
            updated_line = {}
            # 检查并更新每个轴的位置
            values = [None, None, None, None, None, None]  # 对应于A, C, X, Y, Z
            axes = ['A', 'C', 'X', 'Y', 'Z','N']
            for i, axis in enumerate(axes):
                if axis in code_line and code_line.get(axis) is not None:
                    # 应用偏置，如果有必要的话
                    offset = spindle_to_workpiece_offset.get(axis, 0)
                    # 对于AC轴，将角度转换为弧度，并应用偏置(偏置为0)
                    if (axis in ['A', 'C']):
                        values[i] = math.radians(code_line[axis]) + offset*0
                        while values[i] < -np.pi:
                            values[i] += 2 * np.pi
                        while values[i] > np.pi:
                            values[i] -= 2 * np.pi
                        pass
                    # 对于XYZ轴，将毫米转换为米，并应用偏置
                    elif axis in ['X', 'Y','Z']:  # 对于X, Y, Z轴
                        values[i] = -code_line[axis] / 1000.0 - offset
                    else:
                        values[i] = code_line[axis]

            joint_values_list.append(values)

        # # 检查并调整C值
        # for values in joint_values_list:
        #     if values[1] is not None:  # 检查C值
        #         while values[1] < -3.14:
        #             values[1] += 2 * np.pi
        #         while values[1] > 3.14:
        #             values[1] -= 2 * np.pi

        return joint_values_list


    def make_C_continue(self,last_joint_value=0,this_joint_value=0,c_index=1,wind=1):
        '''
        当机床需要C轴连续旋转加工时，确保机床过零点时的旋转是连续的
        C轴的物理角度范围是[-6.28,6.28]，但是在解算的关节角中，角度范围是[-3.14,3.14]
        wind是一个容差
        :return:
        '''

        if np.pi-wind<last_joint_value<np.pi and -np.pi+wind>this_joint_value>-np.pi:
            last_joint_value_ = last_joint_value-2*np.pi
            p.resetJointState(self.id_robot,c_index,last_joint_value_)
        elif -np.pi+wind>last_joint_value>-np.pi and np.pi-wind<this_joint_value<np.pi:
            last_joint_value_ = last_joint_value + 2*np.pi
            p.resetJointState(self.id_robot,c_index,last_joint_value_)

        pass



    def update_machine_state(self, joint_values_list, mode="Reset",tolerance=1e-2,time_scale=1.0,xyzVelocity=0.1,acVelocity=0.5,show_state=True):
        """
        重置机床各轴的位置。

        参数:
        - body_id: 机床的body ID。
        - joint_indices: 一个包含机床各轴对应的关节索引的列表。
        """
        # 遍历所有关节索引，并将其位置重置为0
        axes = ['A', 'C', 'X', 'Y', 'Z', 'N']  # 定义轴的顺序
        joint_indices = list(range(len(axes)))
        def has_reached_target(target_values, tolerance):

            current_positions = [p.getJointState(self.id_robot, i)[0] for i in joint_indices]
            if_return = all( not target or (abs(current - target) < tolerance) for current, target in zip(current_positions, target_values))
            return if_return
        id = 0
        if mode=="Reset":
            for joint_values in joint_values_list:
                id+=1
                for i, axis_value in enumerate(joint_values):
                    if axis_value is not None and axes[i] in ['A', 'C', 'X', 'Y', 'Z']:  # 确保该轴有值
                        p.resetJointState(self.id_robot, jointIndex=i, targetValue=axis_value)
                p.stepSimulation()
                time.sleep(1*time_scale/240.)
                if show_state:
                    print(
                        f"{int(joint_values[axes.index('N')]) if axes.index('N')<len(joint_values) else id} NC code: {[f'{axes[idx]}:{pos:.4f}'  if pos is not None else f'{axes[idx]}:None' for idx, pos in enumerate(joint_values)]}")

        else:
            for joint_values in joint_values_list:
                id+=1
                current_joints = [p.getJointState(self.id_robot, i)[0] for i in joint_indices]
                # self.interpolation_path([current_joints,joint_values],)
                for i, axis_value in enumerate(joint_values):
                    maxVelocity = acVelocity if i in [0,1] else xyzVelocity
                    if axis_value is not None and axes[i] in ['A', 'C', 'X', 'Y', 'Z']:  # 确保该轴有值
                        if axes[i] == 'C' and self.C_continue:
                            self.make_C_continue(current_joints[i],axis_value,i,wind=1)
                            pass
                        p.setJointMotorControl2(bodyUniqueId=self.id_robot,
                                                jointIndex=i,
                                                controlMode=p.POSITION_CONTROL,
                                                targetPosition=axis_value,
                                                targetVelocity=0.0,
                                                positionGain=0.2,  # KP
                                                velocityGain=0.5,  # KD
                                                force=100000,
                                                maxVelocity=maxVelocity,
                                                )

                joint_values_for_judge = np.delete(joint_values, axes.index('N'))
                while not has_reached_target(joint_values_for_judge, tolerance):
                    p.stepSimulation()
                    time.sleep(1*time_scale/240.)


                print(
                    f"{int(joint_values[axes.index('N')]) if axes.index('N') < len(joint_values) else id} NC code: {[f'{axes[idx]}:{pos:.4f}' if pos is not None else f'{axes[idx]}:None' for idx, pos in enumerate(joint_values)]}")

    def execute_nc_code(self, file_path):
        """
        解析并执行NC代码。

        参数:
        - file_path: .tp文件的路径。
        """
        # 解析NC代码
        parsed_values = self.parse_nc_code(file_path)

        # 将NC代码转换到机床坐标系
        transformed_values = self.transform_nc_code_to_machine_coords(parsed_values, self.workpiece_pose,
                                                                      self.workpiece_orientation)
        # transformed_values = parsed_values
        # 获取轴位置
        joint_values_list = self.get_values_with_nc_codes(transformed_values)

        # 更新机床状态
        self.update_machine_state(joint_values_list, mode="Reset")


    def get_to_machine_state(self, joint_values):
        for i,joint_value in enumerate(joint_values):

            if joint_value is not None:  # 确保该轴有值
                p.resetJointState(self.id_robot, jointIndex=i, targetValue=joint_value)
        p.stepSimulation()

        pass




    class PostProcessor:
        def __init__(self, machine):
            self.machine = machine
            self.c_pos_in_a, self.c_ori_in_a = self.machine.get_position_relative_to_link(self.machine.id_robot,
                                                                                self.machine.id_robot,
                                                                                1, 0)
            self.C_offset = self.machine.get_offset(self.machine.id_workpiece, self.machine.id_robot, 0, 1).get('C', 0)
            self.tool_length = None

        def calculate_ac_for_alignment(self, tool_vector):
            """
            计算AC轴的旋转角度，使得刀具轴矢量与世界坐标系的Z轴对齐。
            :param tool_vector: 刀具轴矢量在转台坐标系下的表示。
            :return: A和C轴的旋转角度。
            """
            z_axis = np.array([0, 0, 1])
            rotation, _ = R.align_vectors([tool_vector], [z_axis])
            euler_angles = rotation.as_euler('zyx', degrees=True)
            return euler_angles[0], euler_angles[1]

        def calculate_a_rotation_matrix(self, a_angle):
            """
            计算A轴的旋转矩阵。
            :param a_angle: A轴的旋转角度（弧度）。
            :return: A轴的旋转矩阵。
            """
            return R.from_euler('x', a_angle).as_matrix()

        def calculate_c_rotation_matrix(self, c_angle):
            """
            计算C轴的旋转矩阵。
            :param c_angle: C轴的旋转角度（弧度）。
            :return: C轴的旋转矩阵。
            """
            return R.from_euler('z', c_angle).as_matrix()

        def get_homogeneous_transform(self, rotation_matrix, translation_vector):
            """
            构建齐次变换矩阵。
            :param rotation_matrix: 旋转矩阵 (3x3)。
            :param translation_vector: 平移向量 (3,)。
            :return: 齐次变换矩阵 (4x4)。
            """

            transform = np.eye(4)
            transform[:3, :3] = rotation_matrix
            transform[:3, 3] = translation_vector
            return transform

        def get_ac_transform(self, a_angle, c_angle):
            """
            构建从A到C轴的运动链。
            :param a_angle: A轴的偏摆角度（弧度）。
            :param c_angle: C轴的偏摆角度（弧度）。
            :return: 从A到C的变换矩阵。
            C轴原点
            (-2.8932263198042747e-18, 1.9947784726516383e-17, 0.6855000257492065)
            """
            # 计算A轴的旋转矩阵
            a_rotation_matrix = self.calculate_a_rotation_matrix(-a_angle)
            a_transform = self.get_homogeneous_transform(a_rotation_matrix, [0, 0, 0])

            # 获取C轴在A轴下的位置和姿态
            # c_pos_in_a, c_ori_in_a = self.machine.get_position_relative_to_link(self.machine.id_robot, self.machine.id_robot,
            #                                                             1, 0)
            c_rotation_matrix_in_a = np.array(p.getMatrixFromQuaternion(self.c_ori_in_a)).reshape(3, 3)
            c_transform_in_a = self.get_homogeneous_transform(c_rotation_matrix_in_a, self.c_pos_in_a)

            # 计算C轴的旋转矩阵
            c_rotation_matrix = self.calculate_c_rotation_matrix(-c_angle)
            c_transform = self.get_homogeneous_transform(c_rotation_matrix, [0, 0, 0])

            # 组合变换矩阵
            combined_transform = np.dot(a_transform, np.dot(c_transform_in_a, c_transform))
            return combined_transform



        def apply_workpiece_offset(self,nc_codes ):
            transformed_codes = []
            last_A, last_C = 0, 0
            for code_line in tqdm(nc_codes, desc="Processing NC codes:应用工件到转台的偏置"):
                transformed_line = {}
                A, C = code_line.get('A', last_A),  code_line.get('C', last_C)
                combined_transform = self.get_ac_transform(math.radians(A), math.radians(C) + self.C_offset)
                last_A, last_C = A, C
                workpiece_pose_in_C = np.array([self.machine.workpiece_pose[0]*1000, self.machine.workpiece_pose[1]*1000, self.machine.workpiece_pose[2]*1000,1])
                for axis,value in  code_line.items():
                    if axis in ['X','Y','Z']:
                        i = ['X','Y','Z'].index(axis)
                        offset_vector = np.dot(combined_transform, workpiece_pose_in_C) - np.dot(combined_transform, [0,0,0,1])
                        transformed_line[axis] = value + offset_vector[i]

                    elif axis in ['C']:
                        transformed_line[axis] = value + math.degrees(self.C_offset)
                    elif axis in ['A','N']:
                        transformed_line[axis] = value
                # if 'A' not in transformed_line:
                #     transformed_line['A'] = last_A
                # if 'C' not in transformed_line:
                #     transformed_line['C'] = last_C

                transformed_codes.append(transformed_line)
            return transformed_codes

        def create_kinematic_chain(self,data,W_pos_in_C=None, W_ori_in_C=None,G54=None,tool_length=None):
            '''
            创建一个机器人的运动链，包括所有的关节和连接。
            ACXYZ形式
            这里G54就是编码器返回的工件坐标系的位置[x,y,z]
            sw中测试G54的值为[0.7236,0.269,0.033]

            :return:
            '''
            A,C,X,Y,Z = np.radians(data['A']),np.radians(data['C']),data['X']/1000,data['Y']/1000,data['Z']/1000
            # 工件坐标系到C轴坐标系的变换
            if W_pos_in_C is None:
                W_pos_in_C = [0, 0, 0]
            if W_ori_in_C is None:
                W_ori_in_C = [0, 0, 0, 1]
            self.T_C2Workpicece = Robot.TAB_with_AinW_and_BinW(W_pos_in_C, W_ori_in_C,[0,0,0],[0,0,0,1])

            # C轴坐标系到A轴坐标系的变换
            self.P_A2C = self.c_pos_in_a   # C轴在A轴坐标系下的位置   # [x,y,z]
            temp_T = self.create_transformation_matrix(self.P_A2C, 'none', 0)
            temp_R = self.create_transformation_matrix([0,0,0], 'z', C)
            self.T_A2C = temp_T@ temp_R


            # A轴坐标系到机床坐标系的变换
            self.T_M2A = self.create_transformation_matrix([0, 0, 0], '-x', A)

            # 机床坐标系到工具坐标系的变换
            # 初始时工具坐标系和工件坐标系重合
            self.T0_M2T = self.create_transformation_matrix(self.P_A2C, 'none', 0) @ self.create_transformation_matrix(W_pos_in_C, 'none', 0)



            if tool_length is None:
                # G54 应该包含了刀尖点的偏置，所以这里的tool_length应该是0
                if self.machine.tool_length:
                    self.tool_length = self.machine.tool_length
                else:
                    self.tool_length = 0
            else:
                self.tool_length = tool_length

            if G54 is not None:
                X = X - G54[0]
                Y = Y - G54[1]
                Z = Z - G54[2]

            self.T_M2T = self.T0_M2T @ self.create_transformation_matrix([X,Y,Z-self.tool_length], 'none', 0)

            self.T_T2W = np.linalg.inv(self.T_M2T) @ self.T_M2A @ self.T_A2C @ self.T_C2Workpicece
            self.T_W2T = np.linalg.inv(self.T_T2W)

            P_W = self.T_W2T
            pos = P_W[:3,3]
            return pos

            pass

        def caculate_kinematic_chain(self,data):
            A,C,X,Y,Z = data['A'],data['C'],data['X'],data['Y'],data['Z']
            # 工件坐标系到C轴坐标系的变换
            self.T_C2Workpicece = Robot.TAB_with_AinW_and_BinW([0, 0, 0], [0, 0, 0, 1], [0, 0, 0], [0, 0, 0, 1])

            # C轴坐标系到A轴坐标系的变换
            self.P_A2C = self.c_pos_in_a




        def create_transformation_matrix(self, translation, axis, theta):
            """
            创建一个包含平移和旋转的变换矩阵。

            参数:
            - translation: 平移向量 (tx, ty, tz)
            - axis: 旋转轴, 可以是 'x', 'y', 或 'z'
            - theta: 旋转角度 (弧度)

            返回:
            - transformation_matrix: 4x4 的变换矩阵
            """

            # 创建一个4x4的单位矩阵
            transformation_matrix = np.eye(4)

            # 设置平移部分
            transformation_matrix[0, 3] = translation[0]
            transformation_matrix[1, 3] = translation[1]
            transformation_matrix[2, 3] = translation[2]

            # 创建旋转矩阵
            if axis == 'x':
                R = np.array([
                    [1, 0, 0],
                    [0, np.cos(theta), -np.sin(theta)],
                    [0, np.sin(theta), np.cos(theta)]
                ])
            elif axis == '-x':
                R = np.array([
                    [1, 0, 0],
                    [0, np.cos(-theta), -np.sin(-theta)],
                    [0, np.sin(-theta), np.cos(-theta)]
                ])
            elif axis == 'y':
                R = np.array([
                    [np.cos(theta), 0, np.sin(theta)],
                    [0, 1, 0],
                    [-np.sin(theta), 0, np.cos(theta)]
                ])
            elif axis == '-y':
                R = np.array([
                    [np.cos(-theta), 0, np.sin(-theta)],
                    [0, 1, 0],
                    [-np.sin(-theta), 0, np.cos(-theta)]
                ])
            elif axis == 'z':
                R = np.array([
                    [np.cos(theta), -np.sin(theta), 0],
                    [np.sin(theta), np.cos(theta), 0],
                    [0, 0, 1]
                ])
            elif axis == '-z':
                R = np.array([
                    [np.cos(-theta), -np.sin(-theta), 0],
                    [np.sin(-theta), np.cos(-theta), 0],
                    [0, 0, 1]
                ])
            elif axis == 'none':
                R = np.eye(3)
            else:
                raise ValueError("Invalid axis. Choose from 'x', 'y', or 'z'.")

            # 插入旋转矩阵到变换矩阵的左上角
            transformation_matrix[:3, :3] = R

            return transformation_matrix

        def create_transformation_matrix_sym(self,translation:(list[sym.Symbol]|list[float|int]), axis, theta:sym.Symbol|float|int):
            """
            创建一个包含平移和旋转的符号变换矩阵。

            参数:
            - translation: 平移向量 (tx, ty, tz)
            - axis: 旋转轴, 可以是 'x', 'y', 'z', '-x', '-y', '-z' 或 'none'
            - theta: 旋转角度 (弧度), 符号变量

            返回:
            - transformation_matrix: 4x4 的变换矩阵 (符号矩阵)
            """

            # for t in translation:
            #     if not isinstance(t,(sym.Symbol,int,float)):
            #         raise ValueError("Invalid translation.")
            # if not isinstance(theta,(sym.Symbol,int,float)):
            #     raise ValueError("Invalid theta.")

            # 创建符号变量
            tx, ty, tz = translation[0],translation[1],translation[2]

            # 创建4x4的单位矩阵
            transformation_matrix = sym.Matrix.eye(4)

            # 设置平移部分
            transformation_matrix[0, 3] = tx
            transformation_matrix[1, 3] = ty
            transformation_matrix[2, 3] = tz

            # 创建旋转矩阵
            if axis == 'x':
                R = sym.Matrix([
                    [1, 0, 0],
                    [0, sym.cos(theta), -sym.sin(theta)],
                    [0, sym.sin(theta), sym.cos(theta)]
                ])
            elif axis == '-x':
                R = sym.Matrix([
                    [1, 0, 0],
                    [0, sym.cos(-theta), -sym.sin(-theta)],
                    [0, sym.sin(-theta), sym.cos(-theta)]
                ])
            elif axis == 'y':
                R = sym.Matrix([
                    [sym.cos(theta), 0, sym.sin(theta)],
                    [0, 1, 0],
                    [-sym.sin(theta), 0, sym.cos(theta)]
                ])
            elif axis == '-y':
                R = sym.Matrix([
                    [sym.cos(-theta), 0, sym.sin(-theta)],
                    [0, 1, 0],
                    [-sym.sin(-theta), 0, sym.cos(-theta)]
                ])
            elif axis == 'z':
                R = sym.Matrix([
                    [sym.cos(theta), -sym.sin(theta), 0],
                    [sym.sin(theta), sym.cos(theta), 0],
                    [0, 0, 1]
                ])
            elif axis == '-z':
                R = sym.Matrix([
                    [sym.cos(-theta), -sym.sin(-theta), 0],
                    [sym.sin(-theta), sym.cos(-theta), 0],
                    [0, 0, 1]
                ])
            elif axis == 'none':
                R = sym.Matrix.eye(3)
            else:
                raise ValueError("Invalid axis. Choose from 'x', '-x', 'y', '-y', 'z', '-z' or 'none'.")

            # 插入旋转矩阵到变换矩阵的左上角
            transformation_matrix[:3, :3] = R

            return transformation_matrix

        def create_kinematic_chain_sym(self, W_pos_in_C=None, W_ori_in_C=None, G54=None, tool_length=None,save_file_name=None,ifshow=False):
            """
            创建一个机器人的符号运动链，包括所有的关节和连接。

            参数:
            - data: 机器人参数，包括 A, C, X, Y, Z
            - W_pos_in_C: 工件坐标系在C轴坐标系下的位置
            - W_ori_in_C: 工件坐标系在C轴坐标系下的方向
            - G54: 工件坐标系的偏移
            - tool_length: 工具长度

            返回:
            - pos: 工件坐标系相对于基坐标系的位姿（符号矩阵）
            """
            A, C, X, Y, Z = sym.symbols('A C X Y Z')

            # 工件坐标系到C轴坐标系的变换
            if W_pos_in_C is None:
                W_pos_in_C = [0, 0, 0]
            if W_ori_in_C is None:
                W_ori_in_C = [0, 0, 0, 1]
            self.T_C2Workpicece = Robot.TAB_with_AinW_and_BinW(W_pos_in_C, W_ori_in_C, [0, 0, 0], [0, 0, 0, 1])

            # C轴坐标系到A轴坐标系的变换
            self.P_A2C = self.c_pos_in_a  # C轴在A轴坐标系下的位置   # [x,y,z]
            temp_T = self.create_transformation_matrix_sym(self.P_A2C, 'none', 0)
            temp_R = self.create_transformation_matrix_sym([0, 0, 0], '-z', C)
            self.T_A2C = temp_T @ temp_R

            # A轴坐标系到机床坐标系的变换
            self.T_M2A = self.create_transformation_matrix_sym([0, 0, 0], '-x', A)

            # 机床坐标系到工具坐标系的变换
            # 初始时工具坐标系和工件坐标系重合
            self.T0_M2T = self.create_transformation_matrix_sym(self.P_A2C, 'none', 0) @ self.create_transformation_matrix_sym(
                W_pos_in_C, 'none', 0)

            if tool_length is None:
                # G54 应该包含了刀尖点的偏置，所以这里的tool_length应该是0
                if self.machine.tool_length:
                    self.tool_length = self.machine.tool_length
                else:
                    self.tool_length = 0
            else:
                self.tool_length = tool_length

            if G54 is not None:
                X = X - G54[0]
                Y = Y - G54[1]
                Z = Z - G54[2]

            self.T_M2T = self.T0_M2T @ self.create_transformation_matrix_sym([X, Y, Z - self.tool_length], 'none', 0)

            self.T_T2W = self.T_M2T.inv() @ self.T_M2A @ self.T_A2C @ self.T_C2Workpicece

            self.T_W2T = self.T_T2W.inv()
            if isinstance(save_file_name,str):
                self.save_kinematic_chain_sym(filename=save_file_name)

            if ifshow:
                sym.pprint(self.T_W2T)
            pos = self.T_W2T[:3, 3]

            return self.T_W2T


        def save_kinematic_chain_sym(self,expr=None,file_path=r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\kinematic_chain",filename="kinematic_chain",extension='pkl'):
            if expr is None:
                expr = self.T_W2T
            output_filename = f"{file_path}/{filename}.{extension}"
            with open(output_filename,'wb') as file:
                pickle.dump(expr,file)
            print(f"kinematic saved as {output_filename}")
            pass

        @classmethod
        def load_kinematic_chain_sym(self,file_path=r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\kinematic_chain",filename="kinematic_chain",extension='pkl'):
            """
            从文件加载符号运动链。

            参数:
            - file_path: 保存文件的路径，默认为 "kinematic_chain.pkl"。

            返回:
            - expr: 加载的符号表达式。
            """
            output_filename = f"{file_path}/{filename}.{extension}"

            # 从文件加载表达式
            with open(output_filename, 'rb') as file:
                expr = pickle.load(file)
            print(f"运动链已从 {filename} 加载")

            return expr

        @classmethod
        def evaluate_kinematic_chain_sym(self,expr:sym.Matrix, values_dict:dict):
            """
            求解符号运动链。

            参数:
            - expr: 符号表达式。
            - values_dict: 一个包含符号变量和数值的字典，例如 {A: 30, C: 45, X: 1000, Y: 2000, Z: 3000}。

            返回:
            - evaluated_expr: 计算后的数值表达式。
            """
            # 将字符对象转化为符号对象
            symbol_dict = {}
            for key, value in values_dict.items():
                if isinstance(key, str):
                    symbol_key = sym.symbols(key)
                    if key in ['A', 'C']:
                        symbol_dict[symbol_key] = sym.rad(value)
                        # 将长度单位从毫米转换为米
                    elif key in ['X', 'Y', 'Z']:
                        symbol_dict[symbol_key] = value / 1000.0
                    else:
                        symbol_dict[symbol_key] = value
                else:
                    symbol_dict[key] = value
            evaluated_expr = expr.subs(symbol_dict)
            evaluated_expr = sym.N(evaluated_expr)  # 将符号表达式转为数值
            return evaluated_expr

    def set_joint_ranges(self, joint_ranges):
        """
        重新设定所有关节的运动范围。

        :param joint_ranges: 列表，包含每个关节的运动范围 (min, max)。
        """
        # 初始化关节范围字典
        self.dynamic_joint_ranges = {i: (None, None) for i in range(self.num_all_joints)}
        for i in range(self.num_all_joints):
            joint_info = p.getJointInfo(self.id_robot, i)
            self.dynamic_joint_ranges[i] = (joint_info[8], joint_info[9])
        for i in range(min(self.num_all_joints,len(joint_ranges))):
            min_range, max_range = joint_ranges[i]
            current_min_range, current_max_range = self.dynamic_joint_ranges[i]
            # 如果上下限均为 None 则跳过
            if min_range is None and max_range is None:
                continue
            # 保持原来的数值
            if min_range is None:
                min_range = current_min_range
            if max_range is None:
                max_range = current_max_range

            p.changeDynamics(self.id_robot, i, jointLowerLimit=min_range, jointUpperLimit=max_range, jointLimitForce=10000,physicsClientId=self.id_client)
            self.dynamic_joint_ranges[i] = (min_range, max_range)
            print(f"Joint {i} range set to [{min_range}, {max_range}]")


def main():
    id_client = p.connect(p.GUI)
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=id_client)
    machine_file_name = "F:\sw\\urdf_files\c501-simple.SLDASM\\urdf\c501-simple.SLDASM.urdf"
    my_machine = Machine(id_client=id_client,c_in_sys0=0.685)
    # machine_file_name = "F:\sw\\urdf_files\mikron\\urdf\mikron.urdf"
    # my_machine = Machine(id_client=id_client,c_in_sys0=0.93999)
    my_machine.C_continue = True
    my_machine.load_urdf(fileName=machine_file_name,basePosition=[0.0,0,0],useFixedBase=True)
    my_machine.init_machine([0,0,0,0,0,0])
    my_machine.f_print=True
    my_machine.get_robot_info()
    # my_machine.show_link_sys(1,type=0)

    # relative_S2C_pos, _ = my_machine.get_position_relative_to_link(5, 1)
    # workpiece_id2 = my_machine.add_workpiece_to_machine("F:\\sw\\urdf_files\\blade_6061\\urdf\\blade_6061.urdf",
    #                                                    position=[0., -0.0, 0], orientation=[0, 0, 0, ]
    #                                                    )
    workpiece_urdf = "F:\\sw\\urdf_files\\blade_6061\\urdf\\blade_6061.urdf"
    workpiece_urdf1 = r"F:\sw\urdf_files\6061_simple\urdf\6061_simple.urdf"
    workpiece_id = my_machine.add_workpiece_to_machine(workpiece_urdf1,
                                                       position=[0.0,0.0,0],orientation=[0,0,0,]
                                                       )



    tool_id = my_machine.add_tool_to_machine("F:\\sw\\urdf_files\\tool_6mm.SLDASM\\urdf\\tool_6mm.SLDASM.urdf"
                                             ,tool_length=0.15)
    p.setCollisionFilterPair(workpiece_id, tool_id, -1, -1, 0)
    p.stepSimulation()

    my_machine.parse_nc_code(
        # "F:\\python\\python-vtk\\pybulletProject\\cutting_with_rolling\\data\\tp_path.txt",
        # "F:\\UG\\blade\\NC_1.tp",
        # r"F:\sw\滚压\用作机械臂\边切边滚实验方案\ug\6061_simple_精加工-连续.tp",
        # r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\6061_C轴连续加工.tp"
        r"F:\python\RobotGUI_2.1\User_Defined_Demos\Robot_Machine\files\C轴往复_mikron.tp"
    )

    joint_values = my_machine.get_values_with_nc_codes()
    joint_values = np.array(joint_values)
    # joint_values = my_machine.interpolation_path(joint_values, scale=1,id_index=-1)   # 在使用连续加工时，不能插值
    # time.sleep(2)
    p.setJointMotorControl2(my_machine.id_robot,4,p.POSITION_CONTROL,0)

    data = {'A':25, 'C':60, 'X': 800, 'Y': 200, 'Z': 200} # 角度制和mm
    my_machine.post_processor.create_kinematic_chain(data,W_pos_in_C=[0,0,0],G54=[0.7236,0.269,0.033],tool_length=0)

    while True:
        # my_machine.update_machine_state(joint_values,mode="Motor")
        # my_machine.update_machine_state(joint_values, mode="Reset",time_scale=1)
        my_machine.update_machine_state(joint_values, mode="Motor", time_scale=0.5, tolerance=1e-3,xyzVelocity=0.2,acVelocity=1)
        # my_machine.get_to_machine_state([0.1,0.1,S2B_offset['X'],S2B_offset['Y'],S2B_offset["Z"]])
        # my_machine.get_to_machine_state([0.1, 0.2, 0,0,0])
        p.stepSimulation()
        # my_machine.show_link_sys(1, 1, type=0)
        time.sleep(1 / 240.)
    pass


def test():
    id_client = p.connect(p.GUI)
    machine_file_name = "F:\sw\\urdf_files\c501-simple.SLDASM\\urdf\c501-simple.SLDASM.urdf"
    my_machine = Machine(id_client=id_client,c_in_sys0=0.685)
    my_machine.load_urdf(fileName=machine_file_name, basePosition=(0, 0, 0),
                            useFixedBase=1)
    workpiece_id = my_machine.add_workpiece_to_machine("F:\\sw\\urdf_files\\blade_6061\\urdf\\blade_6061.urdf")
    while True:
        # my_machine.update_machine_state(joint_values,mode="Motor")
        # my_machine.update_machine_state(joint_values, mode="Reset")
        # my_machine.get_to_machine_state([0.1,0.1,S2B_offset['X'],S2B_offset['Y'],S2B_offset["Z"]])
        # my_machine.get_to_machine_state([0.1, 0.2, 0,0,0])
        p.stepSimulation()
        # my_machine.show_link_sys(1, 1, type=0)
        time.sleep(1 / 240.)
    pass
    pass


def test_kinematic_chain():
    id_client = p.connect(p.GUI)
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=id_client)
    machine_file_name = "F:\sw\\urdf_files\c501-simple.SLDASM\\urdf\c501-simple.SLDASM.urdf"
    my_machine = Machine(id_client=id_client, c_in_sys0=0.685)
    # machine_file_name = "F:\sw\\urdf_files\mikron\\urdf\mikron.urdf"
    # my_machine = Machine(id_client=id_client,c_in_sys0=0.93999)
    my_machine.C_continue = True
    my_machine.load_urdf(fileName=machine_file_name, basePosition=[0.0, 0, 0], useFixedBase=True)
    my_machine.init_machine([0, 0, 0, 0, 0, 0])
    my_machine.f_print = True
    my_machine.get_robot_info()
    # my_machine.show_link_sys(1,type=0)

    # relative_S2C_pos, _ = my_machine.get_position_relative_to_link(5, 1)
    # workpiece_id2 = my_machine.add_workpiece_to_machine("F:\\sw\\urdf_files\\blade_6061\\urdf\\blade_6061.urdf",
    #                                                    position=[0., -0.0, 0], orientation=[0, 0, 0, ]
    #                                                    )
    workpiece_urdf = "F:\\sw\\urdf_files\\blade_6061\\urdf\\blade_6061.urdf"
    workpiece_urdf1 = r"F:\sw\urdf_files\6061_simple\urdf\6061_simple.urdf"
    workpiece_id = my_machine.add_workpiece_to_machine(workpiece_urdf1,
                                                       position=[0.0, 0.0, 0], orientation=[0, 0, 0, ]
                                                       )

    tool_id = my_machine.add_tool_to_machine("F:\\sw\\urdf_files\\tool_6mm.SLDASM\\urdf\\tool_6mm.SLDASM.urdf"
                                             , tool_length=0.15)

    data = {'A': 25, 'C': 60, 'X': 800, 'Y': 200, 'Z': 200}  # 角度制和mm
    my_machine.post_processor.create_kinematic_chain_sym(W_pos_in_C=[0, 0, 0],
                                                         # G54=[0.7236, 0.269, 0.033],
                                                         tool_length=0,save_file_name='c50_kinematic_chain_for_sync_test')
    t1  =time.time()
    chain = my_machine.post_processor.load_kinematic_chain_sym(filename='c50_kinematic_chain')
    t2 = time.time()
    print(f'time:{t2-t1}')
    pos = my_machine.post_processor.evaluate_kinematic_chain_sym(chain,data)[:3, 3]
    print(pos)

if __name__ == '__main__':
    # main()
    # test()
    test_kinematic_chain()
    pass