import requests
import json
from langchain.tools import tool  # ✅ 直接使用装饰器

SIMULATION_API_URL = "http://127.0.0.1:8000/simulation"

@tool
def start_simulation():
    """ 调用 API 服务器来启动仿真环境 """
    url = f"{SIMULATION_API_URL}/start_simulation"
    response = requests.post(url)
    return response.json()

@tool
def clear_env():
    """ 调用 API 服务器来清空仿真环境 """
    url = f"{SIMULATION_API_URL}/clear_env"
    response = requests.post(url)
    return response.json()


@tool
def load_robot(urdf_path: str,description, base_position=None, base_orientation=None):
    """
    加载一个 URDF 机械臂到仿真环境中。

    参数:
    - urdf_path (str): URDF 文件的路径
    - description (str): 对任务的详细复述
    - base_position (list, optional): 机械臂的基座位置 (默认 [0, 0, 0])
    - base_orientation (list, optional): 机械臂的基座方向 (默认 [0, 0, 0, 1]，四元数)


    返回:
    - dict: API 响应数据，包含 `status` 和 `robot_id`
    """
    if base_position is None:
        base_position = [0, 0, 0]
    if base_orientation is None:
        base_orientation = [0, 0, 0, 1]

    headers = {"Content-Type": "application/json"}
    data = {
        "urdf_path": urdf_path,
        "basePosition": base_position,
        "baseOrientation": base_orientation,
    }

    try:
        url = f"{SIMULATION_API_URL}/load_robot"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

@tool
def move_robot_to_target(description, robot_id, target_position, target_orientation, max_velocity=1):
    """
    控制机械臂末端移动到目标位置。

    参数:
    - description (str): 对任务的详细复述
    - robot_id (int): 机械臂的 ID
    - target_position (list): 目标位置
    - target_orientation (list,optional): 目标方向 (默认 None)
    - max_velocity (float, optional): 最大速度 (默认 1)

    返回:
    - dict: API 响应数据，包含 `status` 和 `message`
    """
    headers = {"Content-Type": "application/json"}
    data = {
        "robot_id": robot_id,
        "target_position": target_position,
        "target_orientation": target_orientation,
        "maxVelocity": max_velocity,
    }

    try:
        url = f"{SIMULATION_API_URL}/move_robot_to_target"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

@tool
def get_robot_end_pos_and_ori(description,robot_id):
    """
    获取机械臂末端位置。

    参数:
    - description (str): 对任务的详细复述
    - robot_id (int): 机械臂的 ID

    返回:
    - dict: API 响应数据，包含 `status`、`end_pos` 和 `end_ori`
    """
    headers = {"Content-Type": "application/json"}
    data = {"robot_id": robot_id}

    try:
        url = f"{SIMULATION_API_URL}/get_robot_end_pos_and_ori"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


@tool
def create_cube(description,pos, ori, half_extents, mass, color):
    """
    创建一个立方体。

    参数:
    - description (str): 对任务的详细复述
    - pos (list): 位置
    - ori (list): 方向
    - half_extents (list[float]): 半边长, 默认为 [0.05, 0.05, 0.05]
    - mass (float): 质量
    - color (listlist[float]): 颜色, 默认为 [1, 1, 1, 1],其中前三个数值代表颜色(R,G,B)，最后一个数值代表透明度

    返回:
    - dict: API 响应数据，包含 `status` 和 `cube_id`
    """
    headers = {"Content-Type": "application/json"}
    data = {
        "pos": pos,
        "ori": ori,
        "half_extents": half_extents,
        "mass": mass,
        "color": color,
    }

    try:
        url = f"{SIMULATION_API_URL}/create_cube"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


@tool
def get_object_pos_and_ori(description,object_id):
    """
    获取物体的位置和方向。

    参数:
    - description (str): 对任务的详细复述
    - object_id (int): 物体的 ID

    返回:
    - dict: API 响应数据，包含 `status`、`end_pos` 和 `end_ori`
    """
    headers = {"Content-Type": "application/json"}
    data = {"robot_id": object_id}  # 🚩 这里应该是 object_id 但api代码中写成了 robot_id

    try:
        url = f"{SIMULATION_API_URL}/get_object_pos_and_ori"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}