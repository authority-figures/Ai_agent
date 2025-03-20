import requests
import json
import time

# 定义请求的 URL
url1 = 'http://127.0.0.1:8001/load_robot'
url2 = 'http://127.0.0.1:8001/move_robot_to_target'
url3 = 'http://127.0.0.1:8001/get_robot_end_pos_and_ori'
# 定义请求头
headers = {
    'Content-Type': 'application/json'
}

# 定义请求体数据
data1 = {
    "urdf_path": r"F:\sw\urdf_files\minicobo_v1.4\urdf\minicobo_v1.4.urdf",
    "basePosition": [0,0,0],
    "baseOrientation": [0,0,0,1],
}

robot_id = None
data2 = {
    "robot_id": robot_id,
    "target_position": [0.3,0.3,0.2],
    "target_orientation": [0,0,0,1],
    "maxVelocity" : 10,
}

data3 = {
    "robot_id": robot_id,
}

try:
    # 发送 POST 请求
    response = requests.post(url1, headers=headers, data=json.dumps(data1))
    robot_id = response.json()["robot_id"]

    data3["robot_id"] = robot_id
    response = requests.post(url3, headers=headers, data=json.dumps(data3))
    print(response.json())
    data2["robot_id"] = robot_id
    response = requests.post(url2, headers=headers, data=json.dumps(data2))
    data3["robot_id"] = robot_id
    time.sleep(5)
    response = requests.post(url3, headers=headers, data=json.dumps(data3))
    print(response.json())

    # 检查响应状态码
    if response.status_code == 200:
        # 打印响应的 JSON 数据
        print(response.json())
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)
except requests.RequestException as e:
    print(f"请求发生错误: {e}")