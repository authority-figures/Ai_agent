import pybullet as p
import pybullet_data
import numpy as np
from typing import TypedDict, Annotated, Union, Optional,Type,List
from Robot import Robot


class SimulationEnvironment:
    def __init__(self):
        self.physics_client = None
        self.running = False
        self.time_step = 1 / 240  # 仿真步进时间
        self.robot_id = None
        self.robot_list = []
        self.object_list = []


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
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        p.setGravity(0, 0, -9.81)
        self.running = True
        print("Simulation environment initialized")

    def step_simulation(self):
        """ 进行仿真步进 """
        p.stepSimulation()

    def add_object(self, urdf_path,  basePosition,baseOrientation,useFixedBase):
        """ 向仿真环境添加物体 """
        if basePosition is None:
            basePosition = [0, 0, 0]
        if baseOrientation is None:
            baseOrientation = [0, 0, 0, 1]
        obj_id = p.loadURDF(urdf_path, basePosition=basePosition, baseOrientation=baseOrientation,useFixedBase=useFixedBase)
        return obj_id

    def load_robot(self, urdf_path, basePosition,baseOrientation,useFixedBase):
        """ 加载机械臂 """
        if basePosition is None:
            basePosition = [0, 0, 0]
        if baseOrientation is None:
            baseOrientation = [0, 0, 0, 1]

        robot = Robot(self.physics_client)
        robot.load_urdf(fileName=urdf_path, basePosition=basePosition, useFixedBase=useFixedBase,
                             flags=p.URDF_USE_SELF_COLLISION,
                             )
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
                    robot.id_robot, i, p.POSITION_CONTROL,maxVelocity=maxVelocity, targetPosition=joint_positions[i]
                )
        except Exception as e:
            print(e)
            return "Robot moved failed"

        return "Robot moved successfully"




    def move_robot(self, joint_positions):
        """ 控制机械臂的关节 """
        if self.robot_id is None:
            return "No robot loaded"

        num_joints = p.getNumJoints(self.robot_id)
        for i in range(min(len(joint_positions), num_joints)):
            p.setJointMotorControl2(
                self.robot_id, i, p.POSITION_CONTROL, targetPosition=joint_positions[i]
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
