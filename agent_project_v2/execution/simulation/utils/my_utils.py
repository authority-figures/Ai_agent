import numpy as np
import math
from scipy.spatial.transform import Rotation as R


def linear_interpolation(q1, q2, num_intermediate_points):
    """

    :param q1: 参数空间点
    :param q2: 参数空间点
    :param num_intermediate_points: 插值点数
    :return:
    """
    interpolated_q_list = []
    for t in np.linspace(0, 1, num_intermediate_points):
        interpolated_q = tuple([(1 - t) * q1[i] +
                                t * q2[i] for i in range(len(q1))])
        interpolated_q_list.append(interpolated_q)

    return interpolated_q_list


def distance(q1, q2):
    # Calculate distance between two configurations
    return np.linalg.norm(np.array(q1) - np.array(q2))

def quaternion_to_euler(quaternion):
    """
    将四元数转换为欧拉角（绕X轴、Y轴、Z轴的旋转角度）。

    Args:
        quaternion: 代表旋转的四元数，形如 [x, y, z, w]。

    Returns:
        euler: 欧拉角，形如 [roll, pitch, yaw]，单位为度。
    """
    x, y, z, w = quaternion
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = np.degrees(np.arctan2(sinr_cosp, cosr_cosp))

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if np.abs(sinp) >= 1:
        pitch = np.degrees(np.copysign(math.pi / 2, sinp))  # use 90 degrees if out of range
    else:
        pitch = np.degrees(np.arcsin(sinp))

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = np.degrees(np.arctan2(siny_cosp, cosy_cosp))

    return [roll, pitch, yaw]

def euler_to_quaternion(euler):
    """
    将欧拉角（绕X轴、Y轴、Z轴的旋转角度）转换为四元数。

    Args:
        euler: 欧拉角，形如 [roll, pitch, yaw]，单位为度。

    Returns:
        quaternion: 代表旋转的四元数，形如 [x, y, z, w]。
    """
    roll, pitch, yaw = euler
    cy = np.cos(np.radians(yaw * 0.5))
    sy = np.sin(np.radians(yaw * 0.5))
    cp = np.cos(np.radians(pitch * 0.5))
    sp = np.sin(np.radians(pitch * 0.5))
    cr = np.cos(np.radians(roll * 0.5))
    sr = np.sin(np.radians(roll * 0.5))

    w = cy * cp * cr + sy * sp * sr
    x = cy * cp * sr - sy * sp * cr
    y = sy * cp * sr + cy * sp * cr
    z = sy * cp * cr - cy * sp * sr

    return [x, y, z, w]



import matplotlib.pyplot as plt

def plot_corners_on_canvas(canvas_name, corners, c=0):
    """
    在指定画布上绘制角点。

    Args:
        canvas_name: 画布的标识名称。
        corners: 角点的坐标列表，形如 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]。
    """
    if c==0:
        color = "red"
    elif c==1:
        color = "blue"

    else:
        color = "green"

    # 创建或选择画布
    plt.figure(canvas_name)

    # 绘制角点
    for i, corner in enumerate(corners):
        plt.scatter(corner[0], corner[1], color=color, label=f'Corner {i+1}')

    # 设置坐标轴范围和方向
    plt.xlim(0, 680)
    plt.ylim(0, 680)
    plt.gca().set_aspect('equal', adjustable='box')
    # plt.gca().invert_yaxis()

    # 绘制网格
    plt.grid(True)

def compute_spherical_coordinates(center, radius, phi, theta):
    """
    计算球面坐标，并转换为笛卡尔坐标。

    参数:
    center (array-like): 球心坐标 [x, y, z]
    radius (float): 球半径
    phi (float): 纬度角
    theta (float): 经度角

    返回:
    array: 笛卡尔坐标 [x, y, z]
    """
    x = center[0] + radius * np.sin(phi) * np.cos(theta)
    y = center[1] + radius * np.sin(phi) * np.sin(theta)
    z = center[2] + radius * np.cos(phi)
    return np.array([x, y, z])


def sample_sphere_points(center, radius, num_samples, randomize=True, orientation_point=None,change_orientation=False):
    """
    生成位于北半球的点，优先采集高纬度地区，并计算这些点的四元数姿态。

    参数:
    center (array-like): 球心坐标 [x, y, z]
    radius (float): 球半径
    num_samples (int): 采样点数量
    randomize (bool): 是否随机分布
    orientation_point (array-like, optional): 用于计算四元数的参考点，默认为球心

    返回:
    tuple: 目标点和四元数列表
    """
    if orientation_point is None:
        orientation_point = center

    sampled_points = []

    if not randomize:
        # 非随机分布
        sampled_points.append(center + np.array([0, 0, radius]))  # 北极点
        remaining_samples = num_samples - 1
        latitudes = [np.pi / 4]  # 初始纬度45度
        while remaining_samples > 0:
            new_latitudes = []
            for lat in latitudes:
                num_points_in_lat = min(remaining_samples, 4)  # 每个纬度上最多分布4个点
                for i in range(num_points_in_lat):
                    theta = i * (2 * np.pi / num_points_in_lat)
                    point = compute_spherical_coordinates(center, radius, lat, theta)
                    sampled_points.append(point)
                    remaining_samples -= 1
                if remaining_samples == 0:
                    break
                new_latitudes.append(lat + np.pi / 18)  # 向高纬度增加10度
                new_latitudes.append(lat - np.pi / 18)  # 向低纬度增加10度
            latitudes = new_latitudes
    else:
        # 随机分布
        for _ in range(num_samples):
            phi = np.random.uniform(0, np.pi / 2)  # 纬度角，北半球
            theta = np.random.uniform(0, 2 * np.pi)  # 经度角
            point = compute_spherical_coordinates(center, radius, phi, theta)
            sampled_points.append(point)

    quaternions = []

    if not change_orientation:
        for point in sampled_points:
            # 计算四元数，使其从球心指向球面点
            direction = point - orientation_point
            direction /= np.linalg.norm(direction)

            # Default axis (Z-axis)
            z_axis = np.array([0, 0, 1])

            # Calculate the rotation vector between z_axis and direction
            v = np.cross(z_axis, direction)
            c = np.dot(z_axis, direction)

            if np.linalg.norm(v) < 1e-8:  # If vectors are nearly parallel
                quaternion = np.array([0, 0, 0, 1])
            else:
                v = v / np.linalg.norm(v)
                angle = np.arccos(c)
                quaternion = np.hstack((v * np.sin(angle / 2), np.cos(angle / 2)))

            quaternions.append(quaternion)
    else:
        for point in sampled_points:
            # 计算局部坐标系
            z_axis = point - center
            z_axis /= np.linalg.norm(z_axis)

            # 选取经线上低纬度和高纬度的点
            phi_low = np.arctan2(np.linalg.norm(z_axis[:2]), z_axis[2]) - 0.1
            phi_high = np.arctan2(np.linalg.norm(z_axis[:2]), z_axis[2]) + 0.1
            point_low = compute_spherical_coordinates(center, radius, phi_low, np.arctan2(z_axis[1], z_axis[0]))
            point_high = compute_spherical_coordinates(center, radius, phi_high, np.arctan2(z_axis[1], z_axis[0]))

            # 计算x轴和y轴
            x_axis = np.cross(point_high - center, point_low - center)
            x_axis /= np.linalg.norm(x_axis)
            y_axis = np.cross(z_axis, x_axis)

            # 构建旋转矩阵
            rotation_matrix = np.vstack([x_axis, y_axis, z_axis]).T

            # 转换为四元数
            rotation = R.from_matrix(rotation_matrix)
            quaternion = rotation.as_quat()

            quaternions.append(quaternion)

    return sampled_points, quaternions


def add_debug_sys(p,pos,ori,lifetime=1,physicsClientId=0):
    # 定义轴的长度
    axis_length = 0.1
    rot_matrix = p.getMatrixFromQuaternion(ori)
    rot_matrix = np.array(rot_matrix).reshape(3, 3)
    # 绘制X轴（红色）
    x_axis = rot_matrix @ np.array([axis_length, 0, 0])
    p.addUserDebugLine(pos, pos + x_axis, lineColorRGB=[1, 0, 0], lineWidth=2,
                       lifeTime=lifetime, physicsClientId=physicsClientId)

    # 绘制Y轴（绿色）
    y_axis = rot_matrix @ np.array([0, axis_length, 0])
    p.addUserDebugLine(pos, pos + y_axis, lineColorRGB=[0, 1, 0], lineWidth=2,
                       lifeTime=lifetime, physicsClientId=physicsClientId)

    # 绘制Z轴（蓝色）
    z_axis = rot_matrix @ np.array([0, 0, axis_length])
    p.addUserDebugLine(pos, pos + z_axis, lineColorRGB=[0, 0, 1], lineWidth=2,
                       lifeTime=lifetime, physicsClientId=physicsClientId)
    return pos, ori
    pass

def invert_quaternion(q):
    """
    计算四元数的共轭（逆）。
    :param q: 四元数 [x, y, z, w]
    :return: 四元数的共轭 [-x, -y, -z, w]
    """
    return [-q[0], -q[1], -q[2], q[3]]