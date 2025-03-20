import glob
import os
import numpy as np
import open3d as o3d
import re
import sys
sys.path.append('F:/python/CV')

def count_files_with_extension(directory, extension):
    # 构建搜索路径
    search_pattern = os.path.join(directory, f"*.{extension}")
    # 使用 glob 模块获取匹配的文件列表
    files = glob.glob(search_pattern)
    # 返回文件数量
    return len(files)


# def save_RGBDimgs(rgb_image, depth_image, filename):
#     # 保存RGB图像和深度图到一个npz文件中
#     np.savez(filename, rgb=rgb_image, depth=depth_image)

def save_RGBDimgs(rgb_image, depth_image, output_directory='F:/python/CV/cam/test_cam/Dimg', file_prefix='RGBD', extension='npz'):
    # 保存RGB图像和深度图到一个npz文件中
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    # 使用新的计数函数来计算同名前缀文件的数量
    i = count_files_with_prefix(output_directory, file_prefix, extension)
    output_filename = f"{output_directory}/{file_prefix}{i}.{extension}"
    np.savez(output_filename, rgb=rgb_image, depth=depth_image)
    print(f"RGBDimgsColored point cloud saved as {output_filename}")

def count_files_with_prefix(directory, file_prefix, extension):
    """计算具有特定前缀（不包括数字序号）和扩展名的文件数量"""
    pattern = re.compile(rf"^{file_prefix}(\d*)\.{extension}$")
    count = 0
    if not os.path.exists(directory):
        return count
    for filename in os.listdir(directory):
        if pattern.match(filename):
            count += 1
    return count

def save_PointCloud(point_cloud, output_directory='F:\\python\\RobotGUI_2.1\\User_Defined_Demos\\jig\\test_point_cloud\\data', file_prefix='output_colored_point_cloud', extension='pcd'):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    # 使用新的计数函数来计算同名前缀文件的数量
    i = count_files_with_prefix(output_directory, file_prefix, extension)
    output_filename = f"{output_directory}/{file_prefix}{i}.{extension}"
    o3d.io.write_point_cloud(output_filename, point_cloud, write_ascii=True)
    print(f"Colored point cloud saved as {output_filename}")



def convert_units(point_cloud, conversion_factor):
    """将点云的单位转换，conversion_factor是转换因子"""
    points = np.asarray(point_cloud.points)
    points = points * conversion_factor  # 转换坐标单位
    point_cloud.points = o3d.utility.Vector3dVector(points)
    return point_cloud

if __name__ == '__main__':

    # 指定目录路径和后缀名
    directory = f"../point_cloud_data"  # 修改为你的目录路径
    extension = "pcd"  # 修改为你想要统计的后缀名

    # 获取特定后缀名文件的数量
    file_count = count_files_with_extension(directory, extension)
    print(f"目录 '{directory}' 下的 '{extension}' 文件数量为: {file_count}")
