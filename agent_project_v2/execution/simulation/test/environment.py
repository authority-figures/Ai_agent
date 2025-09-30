# simulation_process.py
import pybullet as p
import pybullet_data
import numpy as np
import threading
import time


class SimulationEnvironment:
    def __init__(self, options=""):
        # 连接物理引擎
        self.physics_client = p.connect(p.GUI if options else p.DIRECT, options=options)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=self.physics_client)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1,
                                   physicsClientId=self.physics_client)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.8)

        # 存储仿真中的对象
        self.objects = {}
        self.robots = {}
        self.simulation_time = 0.0
        self.is_running = False
        self.simulation_thread = None

        # 初始化地面
        self.ground_id = p.loadURDF("plane.urdf")
        self.objects[self.ground_id] = {"type": "ground", "name": "Ground"}

        self.base_axis = []

        # 相机配置
        self.camera_config = {
            "distance": 3.0,
            "yaw": 0,
            "pitch": -30,
            "target": [0, 0, 0]
        }

    def initialize(self):

        pass

    def show_axis(self, ifshow=True):
        """显示坐标轴"""
        axis_length = 1.0
        if self.base_axis:
            for line_id in self.base_axis:
                p.removeUserDebugItem(line_id)
            self.base_axis = []
        if not ifshow:
            return
         # X轴红色，Y轴绿色，Z轴蓝色

        x = p.addUserDebugLine([0, 0, 0], [axis_length, 0, 0], [1, 0, 0], lineWidth=2, lifeTime=0)
        y = p.addUserDebugLine([0, 0, 0], [0, axis_length, 0], [0, 1, 0], lineWidth=2, lifeTime=0)
        z = p.addUserDebugLine([0, 0, 0], [0, 0, axis_length], [0, 0, 1], lineWidth=2, lifeTime=0)
        self.base_axis = [x, y, z]

    def add_object(self, urdf_path, position, orientation, name=None):
        """添加物体到仿真环境"""
        orientation = p.getQuaternionFromEuler(orientation)
        obj_id = p.loadURDF(urdf_path, position, orientation)

        if not name:
            name = f"object_{obj_id}"

        self.objects[obj_id] = {
            "type": "object",
            "name": name,
            "urdf": urdf_path,
            "position": position,
            "orientation": orientation
        }
        return obj_id

    def add_robot(self, urdf_path, position, orientation, name):
        """添加机器人到仿真环境"""
        orientation = p.getQuaternionFromEuler(orientation)
        robot_id = p.loadURDF(urdf_path, position, orientation)

        # 获取关节信息
        num_joints = p.getNumJoints(robot_id)
        joints = {}
        for i in range(num_joints):
            joint_info = p.getJointInfo(robot_id, i)
            joints[joint_info[0]] = {
                "name": joint_info[1].decode("utf-8"),
                "type": joint_info[2],
                "lower_limit": joint_info[8],
                "upper_limit": joint_info[9]
            }

        self.robots[robot_id] = {
            "name": name,
            "urdf": urdf_path,
            "position": position,
            "orientation": orientation,
            "joints": joints
        }
        return robot_id

    def set_camera(self, distance, yaw, pitch, target):
        """设置相机视角"""
        self.camera_config = {
            "distance": distance,
            "yaw": yaw,
            "pitch": pitch,
            "target": target
        }
        p.resetDebugVisualizerCamera(
            cameraDistance=distance,
            cameraYaw=yaw,
            cameraPitch=pitch,
            cameraTargetPosition=target
        )

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
        p.resetSimulation()
        self.objects = {}
        self.robots = {}
        self.simulation_time = 0.0

        # 重新添加地面
        self.ground_id = p.loadURDF("plane.urdf")
        self.objects[self.ground_id] = {"type": "ground", "name": "Ground"}

        # 重置相机
        self.set_camera(**self.camera_config)

    def _simulation_loop(self):
        """仿真主循环"""
        while self.is_running:
            self._step_simulation()
            time.sleep(1 / 240)  # 约240Hz

    def _step_simulation(self):
        """执行一步仿真"""
        p.stepSimulation()
        self.simulation_time += 1 / 240

        # 更新对象位置
        for obj_id, obj_info in self.objects.items():
            if obj_info["type"] != "ground":
                pos, orn = p.getBasePositionAndOrientation(obj_id)
                obj_info["position"] = pos
                obj_info["orientation"] = orn

        # 更新机器人状态
        for robot_id, robot_info in self.robots.items():
            pos, orn = p.getBasePositionAndOrientation(robot_id)
            robot_info["position"] = pos
            robot_info["orientation"] = orn

            # 更新关节状态
            for joint_id, joint_info in robot_info["joints"].items():
                joint_state = p.getJointState(robot_id, joint_id)
                joint_info["position"] = joint_state[0]
                joint_info["velocity"] = joint_state[1]

    def get_object_position(self, obj_id):
        """获取物体位置"""
        if obj_id in self.objects:
            return self.objects[obj_id]["position"]
        return None

    def set_robot_joint_position(self, robot_id, joint_id, position):
        """设置机器人关节位置"""
        if robot_id in self.robots and joint_id in self.robots[robot_id]["joints"]:
            p.setJointMotorControl2(
                robot_id,
                joint_id,
                p.POSITION_CONTROL,
                targetPosition=position
            )

    def disconnect(self):
        """断开物理引擎连接"""
        self.stop_simulation()
        p.disconnect(self.physics_client)