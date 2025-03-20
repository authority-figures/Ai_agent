import requests
import json

# 定义请求的 URL
url = 'http://127.0.0.1:8000/simulation/load_robot'

# 定义请求头
headers = {
    'Content-Type': 'application/json'
}


# 定义请求体数据
data = {
    "urdf_path": r"F:\sw\urdf_files\minicobo_v1.4\urdf\minicobo_v1.4.urdf",
    "basePosition": [0,0,0],
    "baseOrientation": [0,0,0,1],
}

# 将请求体数据转换为 JSON 字符串
json_data = json.dumps(data)

try:
    # 发送 POST 请求
    # response = requests.post(url, headers=headers, data=json_data)
    response = requests.post('http://127.0.0.1:8000/simulation/create_cube', headers=headers, data=json.dumps(
        {"pos": [0.3, 0, 0], "ori": [0, 0, 0, 1], "half_extents": [0.1,0.1,0.1], "mass": 1, "color": [0, 1, 0,1]}))
    response2 = requests.post('http://127.0.0.1:8000/simulation/get_object_pos_and_ori', headers=headers, data=json.dumps(
        {"robot_id": 0, }))
    print(response2.json())
    # 检查响应状态码
    if response.status_code == 200:
        # 打印响应的 JSON 数据
        print(response.json())
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)
except requests.RequestException as e:
    print(f"请求发生错误: {e}")