import math
import pybullet as p
import numpy as np
import time
from tqdm import tqdm
import cv2
import os
import sys
import open3d as o3d
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from agent_project.simulation.utils.my_utils import *
from scipy.spatial.transform import Rotation as R
from agent_project.simulation.utils.img_process import *




class Camera:
    def __init__(self, robotId,width=640,height=640,fov=60,aspect=1.0,nearVal=0.1,farVal=2,fps=30, show_cv=True):
        self.robotId = robotId
        self.show_cv = show_cv
        self.fov = fov
        self.nearVal = nearVal
        self.farVal = farVal
        self.width = width
        self.height = height
        self.aspect = self.width / self.height*1.0
        self.focal_length_pixels = self.width/(2*math.tan(math.radians(self.fov)/2))
        self.pos = []
        self.orn = []
        self.fps = fps
        self.projectionMatrix = p.computeProjectionMatrixFOV(fov, self.aspect, self.nearVal, self.farVal)
        self.fx = self.projectionMatrix[0] * width / 2.0
        self.fy = self.projectionMatrix[5] * height / 2.0
        self.cx = width / 2.0
        self.cy = height / 2.0
        self.last_capture_time = time.time()
        pass

    def set_cam_pos(self,Epos,Tpos):
        self.Epos = Epos
        self.Tpos = Tpos
        pass

    def get_pybullet_camera_K(self):
        fx = fy = self.height / (2.0 * math.tan(math.radians(self.fov / 2)))
        cx = self.width / 2.0
        cy = self.height / 2.0

        K = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float64)

        return K

    def convert_corners(self, corners):
        """
        将图像中四个角点的像素坐标转换为以左下角为原点的坐标系。

        参数:
        corners: 一个包含四个角点坐标的列表，每个坐标是(x, y)格式的元组。
        image_height: 图像的高度。

        返回:
        new_corners: 转换后的四个角点坐标列表。
        """
        new_corners = []
        for [x, y] in corners:
            new_x = x
            new_y = self.height - y
            new_corners.append([new_x, new_y])
        return new_corners

    def scale_corners(self, corners, scale):
        """
        将输入的四个角点坐标列表沿着中点扩展或收缩。

        Args:
            corners: 四个角点的坐标列表，形如 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]。
            scale: 扩张的像素点的个数，正值为扩张，负值为收缩。

        Returns:
            scaled_corners: 扩张或收缩后的角点坐标列表，形如 [[x1', y1'], [x2', y2'], [x3', y3'], [x4', y4']]。
        """
        # 计算中点
        center_x = np.mean([corner[0] for corner in corners])
        center_y = np.mean([corner[1] for corner in corners])

        # 对每个角点进行扩张或收缩
        scaled_corners = []
        for corner in corners:
            dx = corner[0] - center_x
            dy = corner[1] - center_y
            scaled_x = center_x + dx * scale
            scaled_y = center_y + dy * scale
            scaled_corners.append([scaled_x, scaled_y])

        return scaled_corners


    def write_text_on_win(self, image, winname, text, position=(10,60)):
        # 在图像上显示误差
        cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1, cv2.LINE_AA)

        # 显示图像
        cv2.imshow(winname, image)
        cv2.waitKey(1)
        pass

    def get_image(self, viewMatrix, projectionMatrix):

        # 计算两次获取图像之间应该有的时间间隔
        interval = 1.0 / self.fps
        current_time = time.time()
        # 只有当达到了时间间隔，才执行获取图像
        if current_time - self.last_capture_time >= interval:
            img_data = p.getCameraImage(int(self.width), int(self.height), viewMatrix, projectionMatrix
                                        ,renderer=p.ER_BULLET_HARDWARE_OPENGL
                                        )
            self.last_capture_time = current_time
            t = time.time()
            return img_data

        return None

    def updata_cam_pos_inRobotSys(self, pos, orn,rot_matrix,fps=30):
        # for _ in range(10):
        #     # p.stepSimulation()
        #     # time.sleep(1.0/240)
        #     pass
        # # time.sleep(1.0/24)
        # # 获取机械臂末端的位置和朝向
        # p.stepSimulation()
        # endEffectorState = p.getLinkState(self.robotId, 5)
        # endEffectorPos = endEffectorState[4]  # 世界坐标系中的位置
        #
        # endEffectorOri = endEffectorState[5]  # 世界坐标系中的朝向（四元数）
        # # 计算旋转矩阵
        # rot_matrix = p.getMatrixFromQuaternion(endEffectorOri)
        # rot_matrix = np.array(rot_matrix).reshape(3, 3)
        #
        # camera_offset_local = np.array(pos)  # 你希望的相机偏移
        # # 将相机偏移从末端执行器坐标系转换到世界坐标系
        # camera_offset_world = np.dot(rot_matrix, camera_offset_local)
        # # 设置相机的位置和朝向以跟随机械臂末端
        # cameraEyePosition = endEffectorPos + camera_offset_world
        cameraEyePosition = pos

        p.addUserDebugPoints([cameraEyePosition],
                             pointColorsRGB=[[0, 1, 0]], pointSize=5, lifeTime=0.1)

        # # 定义沿末端执行器Z轴负方向的向量
        # z_axis_negative_direction = np.array(orn)
        #
        # # 将向量转换到末端执行器的坐标系中
        # camera_target_vector = np.dot(rot_matrix, z_axis_negative_direction)
        camera_target_vector = orn

        # 计算相机的目标位置 观察点
        cameraTargetPosition = cameraEyePosition + camera_target_vector
        p.addUserDebugPoints([cameraTargetPosition],
                             pointColorsRGB=[[1, 1, 0]], pointSize=5, lifeTime=1)

        # cameraTargetPosition = [endEffectorPos[0], endEffectorPos[1], endEffectorPos[2] - 0.1]  # 假设相机向下看
        # cameraTargetPosition = [0,0,0]
        cameraUpVector = -rot_matrix[:, 1]  # Y轴方向
        # 使用更新的相机位置渲染视图
        viewMatrix = p.computeViewMatrix(cameraEyePosition, cameraTargetPosition, cameraUpVector)
        self.Epos = cameraEyePosition
        self.Tpos = cameraTargetPosition



        # img_data = p.getCameraImage(self.width, self.height, viewMatrix, projectionMatrix)
        # 可切换fps
        self.img_data = self.get_image(viewMatrix,self.projectionMatrix)
        if self.img_data:
            self.latest_img_data = self.img_data


        if self.show_cv and self.img_data:
            image = np.reshape(self.img_data[2], (self.img_data[1], self.img_data[0], 4))  # PyBullet返回的是RGBA数据，所以是4通道的

            # 选择性地转换为RGB，如果你不需要Alpha通道
            image = image[:, :, :3]
            self.RGB_img = image
            # OpenCV通常使用BGR格式，所以我们需要从RGBA转换到BGR
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            cv2.imshow('Ori Window', image)
            cv2.waitKey(1)
        return self.img_data
        pass

    def display_depth_image(self, img_data, min_depth, max_depth):
        """
        显示深度图。

        :param img_data: 从 pybullet getCameraImage 返回的图像数据。
        :param min_depth: 深度图归一化的最小距离。
        :param max_depth: 深度图归一化的最大距离。
        """
        # 提取深度图数据
        if img_data is None:
            print("No image data provided.")
            return

        # 从返回的img_data中获取深度图部分
        depth_buffer = img_data[3]
        depth = np.array(depth_buffer)
        # 归一化深度图
        depth = (depth - min_depth) / (max_depth - min_depth)
        depth = np.clip(depth, 0, 1)

        # 将归一化后的深度数据转换为灰度图像
        depth_image = (depth * 255).astype(np.uint8)
        true_depth = self.get_true_depth(img_data)

        # 使用 OpenCV 显示深度图
        cv2.imshow("Depth Image", depth_image)
        cv2.waitKey(1)  # 更新窗口并等待1毫秒，也可以更长时间如果需要


    def get_RGB_img(self,img_data,):
        image = np.reshape(img_data[2], (img_data[1], img_data[0], 4))  # PyBullet返回的是RGBA数据，所以是4通道的

        # 选择性地转换为RGB，如果你不需要Alpha通道
        self.RGB_img = image[:, :, :3]
        return self.RGB_img
        pass

    def get_true_depth(self, img_data,):
        # 深度图转换为实际深度值
        depthImg = img_data[3]
        self.depth_image = 2.0 * self.nearVal * self.farVal / (self.farVal + self.nearVal - (self.farVal - self.nearVal) * (
                    2.0 * np.reshape(depthImg, (self.height, self.width)) - 1.0))
        return self.depth_image
        pass



    def depth_to_pointcloud(self, depth_image, rgb_image, ):
        height, width = depth_image.shape
        xx, yy = np.meshgrid(np.arange(width), np.arange(height))

        # 将像素坐标转换为相机坐标
        x = (xx - self.cx) / self.fx
        y = (yy - self.cy) / self.fy

        # 计算Z坐标并应用深度比例
        z = depth_image
        x = np.multiply(x, z)
        y = np.multiply(y, z)

        # 去除深度值为0的点
        valid_mask = (z > 0) & (z < self.farVal)
        x = x[valid_mask]
        y = y[valid_mask]
        z = z[valid_mask]
        # RGB图像中的颜色值通常在0到255范围内，为了与Open3D兼容，需要将这些值归一化到0到1范围内。
        # colors = rgb_image[yy[valid_mask], xx[valid_mask]] / 255.0  # 归一化颜色值
        colors = rgb_image[valid_mask]
        colors = colors[:, [0, 1, 2]] / 255.0  # 转换BGR到RGB并归一化

        # 创建点云
        points = np.vstack((x, y, z)).transpose()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)  # 设置点云颜色

        return pcd

    def create_transformation_matrix(self, pos, ori):
        """
        Creates a 4x4 transformation matrix from position and orientation (quaternion).

        Args:
            pos (list or np.array): Position [x, y, z].
            ori (list or np.array): Orientation [qx, qy, qz, qw].

        Returns:
            np.array: 4x4 transformation matrix.
        """
        # Convert quaternion to rotation matrix
        rotation = R.from_quat(ori).as_matrix()

        # Create 4x4 transformation matrix
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rotation
        transform_matrix[:3, 3] = pos

        return transform_matrix

    def transform_point_cloud(self, pcd, transform_matrix):
        # 将相机坐标系下的点云转化为世界坐标系
        # 将点云扩展为 (N, 4) 形状，每个点的最后一维是1
        points = np.asarray(pcd.points)
        # 将点云扩展为 (N, 4) 形状，每个点的最后一维是1
        ones = np.ones((points.shape[0], 1))
        points_homogeneous = np.hstack((points, ones))  # (N, 4)

        # 应用变换矩阵
        points_transformed_homogeneous = points_homogeneous @ transform_matrix.T  # (N, 4)

        # 返回 (N, 3) 形状的点云
        points_transformed = points_transformed_homogeneous[:, :3]

        # 创建新的 PointCloud 对象
        pcd_transformed = o3d.geometry.PointCloud()
        pcd_transformed.points = o3d.utility.Vector3dVector(points_transformed)

        # 保留原始的颜色信息（如果有）
        if pcd.has_colors():
            pcd_transformed.colors = pcd.colors

        return pcd_transformed

    @classmethod
    def show_pcd_with_orin(self,pcds=[]):
        if pcds:
            coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1, origin=[0, 0, 0])
            pcds.append(coordinate_frame)
            o3d.visualization.draw_geometries(pcds)
        pass

if __name__ == '__main__':
    """
    d = self.get_true_depth(img_data)
    d, rgb = self.get_true_depth(img_data),self.get_RGB_img(img_data)
    body_pcd1 = self.depth_to_pointcloud(d,rgb)
    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1, origin=[0, 0, 0])
    pos,ori = p.getLinkState(self.camera.id_robot,3)[4],p.getLinkState(self.camera.id_robot,3)[5]
    TF = self.create_transformation_matrix(pos,ori)
    world_pcd1 = self.transform_point_cloud(body_pcd1,TF)
    o3d.visualization.draw_geometries([world_pcd1])
    """

    pass