import time
import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
import pybullet as p
import pybullet_data
import numpy as np
import cv2
from typing import TypedDict, Annotated, Union, Optional,Type,List
from Robot import Robot
from Machine import Machine
from RM_sys import RM_sys
from agent_project.simulation import pb_ompl,taskspaceRRT
from scipy.spatial.transform import Rotation as R

class Calibration_board(Robot):
    def __init__(self, id_client,filePath):
        super().__init__(id_client)
        self.basePosition = [0,0,0]
        self.baseOrientation = [0,0,0,1]
        # self.calibration_board_id = p.loadURDF(filePath, basePosition=self.basePosition, baseOrientation=self.baseOrientation, useFixedBase=True)
        self.load_urdf(fileName=filePath, basePosition=self.basePosition, baseOrientation=self.baseOrientation,useFixedBase=False)
        self.nowPosition = self.basePosition
        self.nowOrientation = self.baseOrientation
        pass


    def reset_position_and_orientation(self,position=None,orientation=None):
        if (position is not None)and(orientation is not None):
            p.resetBasePositionAndOrientation(self.id_robot, posObj=position, ornObj=orientation)
            self.nowPosition = position
            self.nowOrientation = orientation
        else:
            if position is not None:
                p.resetBasePositionAndOrientation(self.id_robot, posObj=position, ornObj=self.nowOrientation)
                self.nowPosition = position
            if orientation is not None:
                p.resetBasePositionAndOrientation(self.id_robot, posObj=self.nowPosition, ornObj=orientation)
                self.nowOrientation = orientation
        pass




class CalibrationPather:
    def __init__(self, robot:pb_ompl.PbOMPLRobot, planner:taskspaceRRT.TaskSpaceRRT, center_pos=None,center_ori=None):
        """
        :param robot: 机械臂控制对象，提供当前状态与运动控制
        :param planner: OMPL 接口对象，负责路径规划
        :param start_position: 起始位置（可以是末端位置，也可以是关节角）
        """
        self.robot = robot
        self.planner = planner
        self.center_pos = center_pos
        self.center_ori = center_ori
        self.T_nine_points = {}

    def set_center(self,center_pos,center_ori):
        self.center_pos = center_pos
        self.center_ori = center_ori
        pass

    def generate_3x3_pos_ori_offsets(self, grid_size_pos=0.01, angle_step_deg=5):
        """
        生成3x3局部位置 + 姿态扰动（顺时针排列，中心点为第一个）

        :param grid_size_pos: 网格间距（单位：米）
        :param angle_step_deg: 姿态扰动角度（单位：度）
        :return: 两个列表：
                 - position_offsets_local: List[np.array([dx, dy, dz])]
                 - rotation_offsets_deg: List[tuple(rx, ry, rz)]，单位：度
        """

        # 顺时针排列的9个位置偏移（局部坐标系下）
        deltas = [-1, 0, 1]
        grid_map = [
            (0, 0),  # 中心点
            (-1, -1),  # 左上
            (0, -1),  # 上
            (1, -1),  # 右上
            (1, 0),  # 右
            (1, 1),  # 右下
            (0, 1),  # 下
            (-1, 1),  # 左下
            (-1, 0),  # 左
        ]

        position_offsets_local = [np.array([dx * grid_size_pos,
                                            dy * grid_size_pos,
                                            0.0]) for dx, dy in grid_map]

        # 姿态扰动设计（绕 x/y 做轻微俯仰/偏转）
        # rotation_offsets_deg = [
        #     (0, 0, 0),  # 0 中心
        #     (-angle_step_deg, -angle_step_deg, -angle_step_deg),  # 1 左上
        #     (0, -angle_step_deg, 0),  # 2 上
        #     (angle_step_deg, -angle_step_deg, angle_step_deg),  # 3 右上
        #     (angle_step_deg, 0, 0),  # 4 右
        #     (angle_step_deg, angle_step_deg, -angle_step_deg),  # 5 右下
        #     (0, angle_step_deg, 0),  # 6 下
        #     (-angle_step_deg, angle_step_deg, angle_step_deg),  # 7 左下
        #     (-angle_step_deg, 0, 0),  # 8 左
        # ]

        rotation_offsets_deg = [
            (0, 0, 0),  # 0 中心
            (-angle_step_deg, angle_step_deg, -angle_step_deg),  # 1 左上
            (-angle_step_deg, -angle_step_deg/2.0, 0),  # 2 上
            (-angle_step_deg, -angle_step_deg, angle_step_deg),  # 3 右上
            (-angle_step_deg, -angle_step_deg*2, 0),  # 4 右
            (angle_step_deg, -angle_step_deg, -angle_step_deg),  # 5 右下
            (angle_step_deg, angle_step_deg/2.0, 0),  # 6 下
            (angle_step_deg, angle_step_deg, angle_step_deg),  # 7 左下
            (angle_step_deg, angle_step_deg*2, 0),  # 8 左
        ]

        return position_offsets_local, rotation_offsets_deg

    def generate_local_targets(self,center_pos, center_ori,
                               position_offsets_local,
                               rotation_offsets_deg,
                               frame='local'):
        """
        生成局部坐标系下带姿态扰动的目标点（位姿）

        :param center_pos: 世界坐标系下中心位置，shape (3,)
        :param center_ori: 世界坐标系下中心姿态（四元数 xyzw），shape (4,)
        :param position_offsets_local: 位置偏移列表（在局部坐标系下），单位：米
                                       List of np.array([dx, dy, dz])
        :param rotation_offsets_deg: 姿态扰动角度（三轴欧拉角，单位：度）
                                     List of (rx_deg, ry_deg, rz_deg)
        :param frame: 'local' 或 'world'，扰动是否在末端局部坐标系下进行
        :return: List of (position, quaternion) 对，表示扰动后的末端位姿（世界坐标系下）
        """
        base_rot = R.from_quat(center_ori)
        base_rot_matrix = base_rot.as_matrix()

        targets = []

        for pos_offset, (rx, ry, rz) in zip(position_offsets_local, rotation_offsets_deg):
            disturb_rot = R.from_euler('xyz', [rx, ry, rz], degrees=True)

            if frame == 'local':
                disturbed_rot = base_rot * disturb_rot  # 当前姿态 * 世界扰动
            elif frame == 'world':
                disturbed_rot = disturb_rot * base_rot  # 局部扰动 * 当前姿态
            else:
                raise ValueError("frame 参数应为 'local' 或 'world'")

            disturbed_ori = disturbed_rot.as_quat()
            disturbed_pos = np.array(center_pos) + base_rot_matrix @ pos_offset

            targets.append((disturbed_pos, disturbed_ori))
        return targets

    def generate_calibration_points(self, grid_size=0.005,angle_step_deg=5,start=[0,0,0,0,0,0]):
        """
        生成九点标定点，并使用规划器进行路径规划

        :param grid_size: 网格之间的间距（单位：米）
        :param center_offset: 九点网格中心相对于起始位置的偏移量 (dx, dy, dz)
        :return: dict，键为点索引，值为规划的路径
        """
        paths = {}
        if self.center_pos is None or self.center_ori is None:
            raise ValueError("中心位置未设置，请先设置中心位置")

        center_pos = np.array(self.center_pos)


        # # 构造九点（3x3）的目标点，相对于中心位置
        # deltas = [ 0,-grid_size, grid_size]
        #
        # offsets_local = [
        #     np.array([dx, dy, 0])   # z=0 表示在末端局部xy平面采样
        #     for dx in deltas for dy in deltas
        # ]
        # position_offsets_local = [np.array([dx, dy, 0.0]) for dx in deltas for dy in deltas]
        # # 将末端姿态转换为旋转矩阵
        # # 如果 center_ori 是四元数：R.from_quat(center_ori)
        # # 如果是欧拉角（假设为 'xyz'）：R.from_euler('xyz', center_ori)
        # rotation_matrix = R.from_quat(self.center_ori).as_matrix()
        #
        # # 将局部坐标系的偏移变换到世界坐标系
        # target_points = [
        #     center_pos + rotation_matrix @ offset_local
        #     for offset_local in offsets_local
        # ]

        position_offsets_local, rotation_offsets_deg = self.generate_3x3_pos_ori_offsets(grid_size,angle_step_deg)
        targets = self.generate_local_targets(self.center_pos, self.center_ori,position_offsets_local, rotation_offsets_deg,'local')




        target_joints = []
        start = start
        for target in targets:
            target_point,target_ori = target
            target_joint = self.robot.get_state_from_ik(target_point, target_ori,
                                                        start=start, maxNumIteration=10000, tcp_name="RGB_camera")
            target_joints.append(target_joint)
            start = target_joint


        for idx, target_joint in enumerate(target_joints):
            pos,ori = self.robot.get_pos_ori_from_ik(target_joint, tcp_name=None)
            T_nine_point = self.robot.pos_to_matrix(pos,ori)
            self.T_nine_points[idx] = T_nine_point



        start_joint = self.robot.get_cur_state()


        for idx, target_joint in enumerate(target_joints):
            self.planner.set_planner("RRTConnect")
            print(f"Planning path to point {idx+1}: {target_joint}")
            pb_ompl.INTERPOLATE_NUM = 500
            ret, path = self.planner.plan_start_goal(start_joint,target_joint)
            start_joint = target_joint
            if path:
                paths[idx] = path
            else:
                print(f"⚠️ 规划到点 {idx+1} 失败")
        return paths

    # def plan_to(self, target_position):
    #     """
    #     使用 OMPL 接口规划从当前机械臂位置到目标位置的路径。
    #
    #     :param target_position: 目标位置 [x, y, z]
    #     :return: 规划路径（可按需求定义返回结构）
    #     """
    #     self.robot.set_state(self.start_pos)
    #     success, path = self.planner.plan_start_goal(goal1,goal2)
    #     if success:
    #         return path
    #     else:
    #         return None








class HandEyeCalibrator:
    def __init__(self,
                 camera_matrix,
                 dist_coeffs=None,
                 pattern_size=(7, 7),
                 square_size=0.002,
                 asymmetric=False):
        """
        初始化手眼标定器（支持圆点阵列）
        :param camera_matrix: 相机内参 (3x3)
        :param dist_coeffs: 畸变参数 (1x5)
        :param pattern_size: 标定板内点数量 (cols, rows)
        :param square_size: 单个格子物理尺寸（单位：米）
        :param asymmetric: 是否为非对称圆点阵
        """
        self.debug = False
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((5, 1))
        self.pattern_size = pattern_size
        self.square_size = square_size
        self.asymmetric = asymmetric

        self.R_gripper2base = []
        self.t_gripper2base = []
        self.R_target2cam = []
        self.t_target2cam = []
        self.T_cam2gripper = None
        self.T_target2base = None

        # 准备标定板3D点
        self.obj_points_3d = self._generate_object_points()


    def get_target2base(self):
        if self.T_cam2gripper is not None:
            T_target2base = np.eye(4)
            T_target2cam = np.eye(4)
            T_target2cam[:3, :3] = self.R_target2cam[0]
            T_target2cam[:3, 3] = self.t_target2cam[0]
            T_gripper2base = np.eye(4)
            T_gripper2base[:3, :3] = self.R_gripper2base[0]
            T_gripper2base[:3, 3] = self.t_gripper2base[0]

            self.T_target2base = T_gripper2base @ self.T_cam2gripper @ T_target2cam
        return  self.T_target2base

    def update_target2base(self,image,robot_pose=None):
        # 使用一张图像更新标定板在基坐标系下的位姿
        # 默认使用储存的第一个机械臂的位姿
        if robot_pose is None:
            robot_pose = np.eye(4)
            robot_pose[:3, :3] = self.R_gripper2base[0]
            robot_pose[:3, 3] = self.t_gripper2base[0]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        flags = cv2.CALIB_CB_ASYMMETRIC_GRID if self.asymmetric else cv2.CALIB_CB_SYMMETRIC_GRID

        ret, centers = cv2.findCirclesGrid(gray, self.pattern_size, flags=flags)

        if not ret:
            print("[×] 未能在图像中识别圆点标定板")
            return False
        else:
            print(f"[✓] 圆点检测成功！绘制识别结果")
            if self.debug:
                vis_img = cv2.drawChessboardCorners(image.copy(), self.pattern_size, centers, ret)
                cv2.imshow("Detected Circles Grid", vis_img)
                cv2.waitKey(1000)
                cv2.destroyWindow("Detected Circles Grid")

        # 估计标定板在相机坐标系下的位姿
        ret, rvec, tvec = cv2.solvePnP(self.obj_points_3d, centers,
                                       self.camera_matrix, self.dist_coeffs)

        if not ret:
            print("[×] solvePnP 失败")
            return False

        R_cam, _ = cv2.Rodrigues(rvec)
        t_cam = tvec.reshape(3)
        T_target2cam = np.eye(4)
        T_target2cam[:3, :3] = R_cam
        T_target2cam[:3, 3] = t_cam
        self.T_target2base = robot_pose @ self.T_cam2gripper @ T_target2cam
        return self.T_target2base.copy()


    def _generate_object_points(self):
        objp = np.zeros((np.prod(self.pattern_size), 3), np.float32)
        if self.asymmetric:
            for i in range(self.pattern_size[1]):
                for j in range(self.pattern_size[0]):
                    objp[i * self.pattern_size[0] + j, :2] = (
                        (2 * j + i % 2) * self.square_size,
                        i * self.square_size
                    )
        else:
            objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
            objp *= self.square_size
        return objp

    def add_sample_from_image(self, image, robot_pose):
        """
        从图像中检测圆点阵列并添加样本（自动识别）
        :param image: 彩色或灰度图
        :param robot_pose: 4x4机械臂末端位姿（base 下）
        :return: 是否成功
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        flags = cv2.CALIB_CB_ASYMMETRIC_GRID if self.asymmetric else cv2.CALIB_CB_SYMMETRIC_GRID

        ret, centers = cv2.findCirclesGrid(gray, self.pattern_size, flags=flags)

        if not ret:
            print("[×] 未能在图像中识别圆点标定板")
            return False
        else:
            print(f"[✓] 圆点检测成功！绘制识别结果")
            if self.debug:
                vis_img = cv2.drawChessboardCorners(image.copy(), self.pattern_size, centers, ret)
                cv2.imshow("Detected Circles Grid", vis_img)
                cv2.waitKey(1000)
                cv2.destroyWindow("Detected Circles Grid")
        # 估计相机相对标定板的位姿
        ret, rvec, tvec = cv2.solvePnP(self.obj_points_3d, centers,
                                       self.camera_matrix, self.dist_coeffs)
        print("→ tvec norm: ", np.linalg.norm(tvec))

        if not ret:
            print("[×] solvePnP 失败")
            return False

        R_cam, _ = cv2.Rodrigues(rvec)
        t_cam = tvec.reshape(3)
        # 添加样本
        self.R_target2cam.append(R_cam)
        self.t_target2cam.append(t_cam)

        self.R_gripper2base.append(robot_pose[:3, :3])
        self.t_gripper2base.append(robot_pose[:3, 3])
        print("→ Robot pose t norm:", np.linalg.norm(robot_pose[:3, 3]))
        print("[✓] 添加样本成功")
        return True

    def calibrate(self, method=cv2.CALIB_HAND_EYE_TSAI):
        """
        执行手眼标定
        :return: 4x4 相机 -> 末端的变换矩阵
        """
        R_cam2gripper, t_cam2gripper = cv2.calibrateHandEye(
            self.R_gripper2base, self.t_gripper2base,
            self.R_target2cam, self.t_target2cam,
            method=method
        )
        T = np.eye(4)
        T[:3, :3] = R_cam2gripper
        T[:3, 3] = t_cam2gripper.ravel()
        self.T_cam2gripper = T
        return T

    def reset(self):
        """清空所有样本"""
        self.R_gripper2base.clear()
        self.t_gripper2base.clear()
        self.R_target2cam.clear()
        self.t_target2cam.clear()


def debug_detect_points():
    from glob import glob
    calibration_data = np.load(
        "/home/lwh/Project/python_project/Ai_agent/agent_project/jaka_work_space/datas/calibration_data.npz",
        allow_pickle=True)
    calibration_data_for_env = np.load(
        "/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_data/calibration_data.npz",
        allow_pickle=True)
    calibration_data = calibration_data_for_env

    # 示例内参矩阵（可从 RealSense 或标定获得）
    K = calibration_data['camera_matrix']

    # 初始化：非对称圆点阵，4x11点，单格 25mm
    calibrator = HandEyeCalibrator(camera_matrix=K,
                                   pattern_size=(7, 7),
                                   square_size=0.002,
                                   asymmetric=False)
    calibrator.debug = True
    # 假设你有一组图像与对应的机械臂位姿
    # image_paths = sorted(glob("images/*.png"))
    # robot_poses = np.load("robot_poses.npy")  # 每个是 4x4 矩阵
    #
    # for img_path, robot_pose in zip(image_paths, robot_poses):
    #     img = cv2.imread(img_path)
    #     calibrator.add_sample_from_image(img, robot_pose)
    data_path = "./test_data/calibration_data.npz"

    for key in calibration_data['point_data'].item().keys():
        print("添加点：", key)
        point_data = calibration_data['point_data'].item()[key]
        image = point_data['img']
        T = point_data['TB2E']
        img = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        calibrator.add_sample_from_image(img, T)

    for i in range(len(calibrator.R_gripper2base)):
        print(f"sample {i}")
        print("robot_t:", calibrator.t_gripper2base[i])
        print("camera_t:", calibrator.t_target2cam[i])

    # 标定
    T = calibrator.calibrate()
    print("\n[✓] 相机 -> 末端变换:\n", T)
    print("\n[✓] 标定板 -> 机械臂基座变换:\n", calibrator.get_target2base())

    # ------------------------------------------------
    point_data = calibration_data_for_env['point_data'].item()['point_0']
    image = point_data['img']
    T = point_data['TB2E']
    img = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    calibrator.update_target2base(img, T)
    print("标定板发生偏差，更新标定板在基坐标系下的位姿")
    print("\n[✓] 标定板 -> 机械臂基座变换:\n", calibrator.T_target2base)




def debug_board():
    physics_client = p.connect(p.GUI)  # GUI 模式
    p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, shadowMapWorldSize=1, shadowMapIntensity=1,
                               physicsClientId=physics_client)
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=physics_client)  # 关闭GUI信息展示
    p.addUserDebugLine([0, 0, 0], [1, 0, 0], lineColorRGB=[1, 0, 0], lineWidth=2)
    p.addUserDebugLine([0, 0, 0], [0, 1, 0], lineColorRGB=[0, 1, 0], lineWidth=2)
    p.addUserDebugLine([0, 0, 0], [0, 0, 1], lineColorRGB=[0, 0, 1], lineWidth=2)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    board_urdf = "./models/calibration_board/urdf/calibration_board.urdf"
    board = Calibration_board(physics_client,board_urdf)
    board.reset_position_and_orientation(position=(0,0,0),
                                         orientation=(0,0,0,1))
    while True:
        p.stepSimulation()
        board.show_link_sys(-1,0,1)
        board.show_link_sys(0, 0, 1)

        time.sleep(1/240.)

    pass

if __name__ == '__main__':
    debug_detect_points()
    # debug_board()


