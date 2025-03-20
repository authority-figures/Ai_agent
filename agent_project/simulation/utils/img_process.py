import cv2
import cv2.aruco as aruco
import numpy as np




def extract_aruco_markers_info(img_data, near_plane, far_plane, ifshow=True):
    """
    从图像中提取ArUco标记的信息。
    PyBullet返回的深度图是归一化的，值在0到1之间，表示从近裁剪面到远裁剪面的相对深度。我们可以根据相机的近裁剪面和远裁剪面距离将这些值转换为实际深度。
    depth=near_plane+(far_plane−near_plane)∗d
    参数:
    - image: 输入图像，numpy数组格式。

    返回:
    - corners: 检测到的所有ArUco标记的角点列表。
    - ids: 检测到的所有ArUco标记的ID列表。
    """
    '''
    # arucoDict = cv2.aruco.Dictionary_get(ARUCO_DICT[args["type"]]) is replaced by:
    arucoDict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT[args["type"]])
    
    # arucoParams = cv2.aruco.DetectorParameters_create() is replaced by:
    arucoParams = cv2.aruco.DetectorParameters()
    
    # detector instanciation
    detector = cv2.aruco.ArucoDetector(arucoDict, arucoParams) 
    
    # corners, ids, rejected = cv2.aruco.detectMarkers(frame, arucoDict, arucoParams) is replaced by:
    corners, ids, rejected = detector.detectMarkers(frame)
    '''
    width, height, rgbImg, depthImg, segImg = img_data[0], img_data[1], img_data[2], img_data[3], img_data[4]
    # 提取RGBA图像
    rgba_image = np.reshape(rgbImg, (height, width, 4))  # PyBullet返回的是RGBA数据，所以是4通道的
    bgr_image = cv2.cvtColor(rgba_image, cv2.COLOR_RGBA2BGR)

    # 深度图转换为实际深度值
    depth_image = 2.0 * near_plane * far_plane / (far_plane + near_plane - (far_plane - near_plane) * (2.0 * np.reshape(depthImg, (height, width)) - 1.0))

    # 定义使用的ArUco字典
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)


    # 创建默认参数的ArUco检测器
    parameters = aruco.DetectorParameters()

    # 检测ArUco标记
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejectedImgPoints = detector.detectMarkers(bgr_image)

    # 提取角点深度信息
    corner_depths = []
    for marker_corners in corners:
        marker_depths = []
        for corner in marker_corners[0]:  # 遍历每个角点
            x, y = int(corner[0]), int(corner[1])
            depth = depth_image[y, x]  # 获取深度值
            marker_depths.append(depth)
        corner_depths.append(marker_depths)

    if ifshow:

        # 如果需要，可以在图像上绘制检测到的标记
        image_with_markers = aruco.drawDetectedMarkers(bgr_image.copy(), corners, ids)

        # 显示带有ArUco标记的图像，这一步在实际应用中可以省略
        cv2.imshow('Detected ArUco markers', image_with_markers)
        cv2.waitKey(1)

    data = [corners, corner_depths, ids, bgr_image]
    return data



def calculate_expected_corners(image, center_point, edge_length, rotation_angle):
    # 获取图像尺寸
    height, width = image.shape[:2]

    # 将中心点坐标从图像中心转换为图像像素坐标
    center_x = int(width / 2 + center_point[0])
    center_y = int(height / 2 - center_point[1])  # Y轴反向

    # 计算期望角点的相对坐标（相对于中心点）
    half_length = edge_length / 2
    corner_offsets = np.array([[-half_length, -half_length],  # 左上
                               [half_length, -half_length],   # 右上
                               [half_length, half_length],  # 右下
                               [-half_length, half_length]]) # 左下

    # 应用偏转角度（绕中心点旋转）
    rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), rotation_angle, 1)
    rotated_corner_offsets = np.matmul(rotation_matrix[:, :2], corner_offsets.T).T

    # 计算期望角点的绝对像素坐标
    expected_corners = rotated_corner_offsets + np.array([center_x, center_y])

    return expected_corners.astype(int)



def calculate_error(corners, ids, desired_pose, image, ifshow=True):

    if len(corners) == 0:
        print("Number of detected corners does not match number of expected corners!")
        return 0
    else:
        corners = corners[0][0]
        pass

    if ifshow:

        # 绘制检测到的角点（红色）
        for i, corner in enumerate(corners):

            corner = tuple(map(int, corner.ravel()))
            cv2.circle(image, corner, 5, (0, 0, 255), -1)
            cv2.putText(image, str(i), corner, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # 绘制期望角点（绿色）
        for i, corner in enumerate(desired_pose):
            corner = tuple(map(int, corner.ravel()))
            cv2.circle(image, corner, 5, (0, 255, 0), -1)
            cv2.putText(image, str(i), corner, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    # 计算误差（示例：使用角点之间的欧氏距离）
    error = 0
    for i in range(len(corners)):
        error += np.linalg.norm(corners[i] - desired_pose[i])

    # 在图像上显示误差
    cv2.putText(image, f'Error: {error}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)

    # 显示图像
    cv2.imshow('Detected Corners', image)
    cv2.waitKey(1)


    return error




def compute_image_jacobian(u, v, Z, f=800, type=0):
    """
    简化的图像雅可比矩阵计算
    """
    if type==0:

        J = np.array([
            [-f/Z, 0, u/Z, u*v/f, -(f**2 + u**2)/f, v],
            [0, -f/Z, v/Z, (f**2 + v**2)/f, -u*v/f, -u]
        ])
    elif type==1:
        J = np.array([
            [f / Z, 0, -u / Z, u * v / f, -(f ** 2 + u ** 2) / f, v],
            [0, f / Z, -v / Z, (f ** 2 + v ** 2) / f, -u * v / f, -u]
        ])
    else :
        J = np.array([
            [f / Z, 0, -u / Z, -u * v / f, (f ** 2 + u ** 2) / f, -v],
            [0, f / Z, -v / Z, -(f ** 2 + v ** 2) / f, u * v / f, u]
        ])

    return J


def calculate_control_command(detected_corners, expected_corners, detected_corners_depth, f=800, alpha=0.01, pid_controller_list=None):
    """
    计算控制命令
    """
    # 假设detected_corners和expected_corners都是[N, 2]的数组
    # 检查期望角点和检测到的角点的数量是否相同
    if len(detected_corners) == 0:
        print("Number of detected corners does not match number of expected corners!")
        return np.zeros(6)
    else:
        detected_corners = detected_corners
    errors = expected_corners - detected_corners

    Js = []
    for corner, depth in zip(detected_corners, detected_corners_depth[0]):
        Su, Sv = corner
        J = compute_image_jacobian(Su, Sv, depth, f,type=0)
        Js.append(J)
    J_stack = np.vstack(Js)  # 将所有雅可比矩阵垂直堆叠

    error_vector = errors.flatten()
    if pid_controller_list is not None:
        pid_output_error_vector = []
        for error, pid_controller in zip(error_vector, pid_controller_list):
            # 使用PID控制器修正控制指令
            pid_output_error = pid_controller.update(error,None)
            pid_output_error_vector.append(pid_output_error)
        pid_output_error_vector = np.array(pid_output_error_vector)
        error_vector = pid_output_error_vector * alpha
    else:
        # 计算误差向量
        error_vector = error_vector * alpha

    # 计算控制命令
    pseudo_inverse_J = np.linalg.pinv(J_stack)
    control_command = np.dot(pseudo_inverse_J, error_vector)

    """
            z方向角速度不用调整，应该是跟图像雅可比矩阵性质相关，wy只与sv(图像坐标)和su相关，我的z轴反向只影响qz的值，
            只会影响xyz的线速度，又因为xy方向和图像是符合要求的，z其实也是相同的，
            就是表示的物理含义是朝向相机，和标准的含义相反，所以只需要改z轴线速度就行了
    """
    control_command = control_command*np.array([1,1,-1,1,1,1])

    return control_command




def calculate_control_command_test(detected_corners, expected_corners, detected_corners_depth, f=800, alpha=1):
    """
    计算控制命令
    """
    # 假设detected_corners和expected_corners都是[N, 2]的数组
    # 检查期望角点和检测到的角点的数量是否相同
    if len(detected_corners) == 0:
        print("Number of detected corners does not match number of expected corners!")
        return np.zeros(6)
    else:
        pass
    errors = expected_corners - detected_corners
    # identity_matrix = np.eye(2)
    # # 将第二列的元素乘以-1
    # identity_matrix[:, 1] *= -1
    # errors = np.dot(errors, identity_matrix)

    Js = []

    for corner, depth in zip(detected_corners, detected_corners_depth[0]):

        Su, Sv = corner
        J = compute_image_jacobian(Su, Sv, -0.4, f, type=1)

        Js.append(J)
    J_stack = np.vstack(Js)  # 将所有雅可比矩阵垂直堆叠

    # 计算误差向量
    error_vector = errors.flatten() * alpha

    # 计算控制命令
    pseudo_inverse_J = np.linalg.pinv(J_stack)
    control_command = np.dot(pseudo_inverse_J, error_vector)

    return control_command