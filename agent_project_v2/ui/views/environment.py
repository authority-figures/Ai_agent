import pybullet as p
import pybullet_data
import numpy as np
import time


class SimulationEnvironment:
    def __init__(self, gui=False):
        self.gui = gui
        self.physics_client = None
        self.objects = {}
        self.robots = {}
        self.camera_params = {
            'distance': 3.0,
            'yaw': 0,
            'pitch': -30,
            'target': [0, 0, 0]
        }
        self.simulation_time = 0.0
        self.running = False
        self.render_width = 800
        self.render_height = 600
        self.rgba_buffer = None
        self.depth_buffer = None
        self.segmentation_buffer = None

    def connect(self):
        """连接到物理引擎"""
        if self.gui:
            self.physics_client = p.connect(p.GUI)
        else:
            self.physics_client = p.connect(p.DIRECT)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

    def disconnect(self):
        """断开物理引擎连接"""
        if self.physics_client is not None:
            p.disconnect(self.physics_client)
            self.physics_client = None

    def load_scene(self, scene_config):
        """加载场景"""
        # 加载地面
        self.objects['ground'] = p.loadURDF("plane.urdf")

        # 加载机器人
        robot_id = p.loadURDF(scene_config['robot_path'], scene_config['robot_position'])
        self.robots['main_robot'] = {
            'id': robot_id,
            'joints': self.get_joint_info(robot_id),
            'position': scene_config['robot_position']
        }

        # 加载其他物体
        for obj in scene_config.get('objects', []):
            obj_id = p.loadURDF(obj['path'], obj['position'])
            self.objects[obj['name']] = obj_id

    def get_joint_info(self, robot_id):
        """获取机器人关节信息"""
        num_joints = p.getNumJoints(robot_id)
        joints = {}
        for i in range(num_joints):
            joint_info = p.getJointInfo(robot_id, i)
            joints[joint_info[1].decode('utf-8')] = {
                'index': i,
                'type': joint_info[2],
                'limits': (joint_info[8], joint_info[9])
            }
        return joints

    def set_camera(self, distance=None, yaw=None, pitch=None, target=None):
        """设置相机参数"""
        if distance is not None:
            self.camera_params['distance'] = distance
        if yaw is not None:
            self.camera_params['yaw'] = yaw
        if pitch is not None:
            self.camera_params['pitch'] = pitch
        if target is not None:
            self.camera_params['target'] = target

    def get_camera_view(self):
        """获取相机视图矩阵"""
        return p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=self.camera_params['target'],
            distance=self.camera_params['distance'],
            yaw=self.camera_params['yaw'],
            pitch=self.camera_params['pitch'],
            roll=0,
            upAxisIndex=2
        )

    def get_camera_projection(self):
        """获取相机投影矩阵"""
        return p.computeProjectionMatrixFOV(
            fov=60, aspect=float(self.render_width) / self.render_height,
            nearVal=0.1, farVal=100.0
        )

    def render(self, width=None, height=None):
        """渲染场景"""
        if width is not None:
            self.render_width = width
        if height is not None:
            self.render_height = height

        view_matrix = self.get_camera_view()
        projection_matrix = self.get_camera_projection()

        # 获取渲染结果
        _, _, rgba, depth, seg = p.getCameraImage(
            width=self.render_width,
            height=self.render_height,
            viewMatrix=view_matrix,
            projectionMatrix=projection_matrix,
            renderer=p.ER_BULLET_HARDWARE_OPENGL
        )

        self.rgba_buffer = rgba
        self.depth_buffer = depth
        self.segmentation_buffer = seg

        return rgba

    def step_simulation(self, dt=1 / 240.):
        """执行仿真步"""
        p.stepSimulation()
        self.simulation_time += dt
        return self.simulation_time

    def start(self):
        """开始仿真"""
        self.running = True

    def stop(self):
        """停止仿真"""
        self.running = False

    def reset(self):
        """重置仿真"""
        self.disconnect()
        self.connect()
        self.simulation_time = 0.0
        self.load_scene(self.scene_config)

    def set_robot_position(self, robot_name, position):
        """设置机器人位置"""
        if robot_name in self.robots:
            p.resetBasePositionAndOrientation(
                self.robots[robot_name]['id'],
                position,
                [0, 0, 0, 1]
            )

    def get_robot_position(self, robot_name):
        """获取机器人位置"""
        if robot_name in self.robots:
            position, orientation = p.getBasePositionAndOrientation(
                self.robots[robot_name]['id']
            )
            return position
        return None

    def set_joint_angle(self, robot_name, joint_name, angle):
        """设置关节角度"""
        if robot_name in self.robots:
            robot = self.robots[robot_name]
            if joint_name in robot['joints']:
                p.setJointMotorControl2(
                    bodyIndex=robot['id'],
                    jointIndex=robot['joints'][joint_name]['index'],
                    controlMode=p.POSITION_CONTROL,
                    targetPosition=angle
                )

    def get_joint_angle(self, robot_name, joint_name):
        """获取关节角度"""
        if robot_name in self.robots:
            robot = self.robots[robot_name]
            if joint_name in robot['joints']:
                joint_state = p.getJointState(
                    robot['id'],
                    robot['joints'][joint_name]['index']
                )
                return joint_state[0]
        return None