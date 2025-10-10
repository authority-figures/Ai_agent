from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, QTimer
from agent_project_v2.ui.widgets.graph_widget import GraphWidget
import requests
import threading
import json
from websocket import create_connection
import socket, time


# 等待后端服务启动
def wait_for_backend(host="localhost", port=8000, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("✅ Backend is ready!")
                return True
        except OSError:
            print("⏳ Waiting for backend to start...")
            time.sleep(0.5)
    print("❌ Backend not available after timeout.")
    return False


class AgentGraphView(QWidget):
    node_selected = pyqtSignal(str)  # 转发信号
    messageState_updated = pyqtSignal(dict)  # 图状态更新信号
    def __init__(self):
        super().__init__()

        self.setup_ui()


        # 指定延迟时间后，执行一次特定的函数 / 槽函数
        QTimer.singleShot(1000, self.fetch_graph_data)  # 获取图结构

        # 连接信号
        self.graph_widget.node_selected.connect(self.node_selected.emit)
        self.start_websocket_listener()



    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("Agent工作流程")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 创建图组件
        self.graph_widget = GraphWidget({})  # 暂时传入空图，后续可以通过update_graph_state更新
        layout.addWidget(self.graph_widget)

    def fetch_graph_data(self):
        """从后端API获取图结构数据"""
        url = "http://localhost:8000/api/graph/graph-structure"
        try:
            # 注意这里的 URL 需要和你的后端 API 地址匹配
            # 如果你的后端运行在本地其他端口（如8000），需要指定
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "success":
                    # 将获取到的数据传递给 graph_widget 进行渲染
                    self.graph_widget.create_graph(data["data"])
                else:
                    print("API returned error:", data.get("detail", "Unknown error"))
            else:
                print(f"HTTP Error: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Network error occurred: {e}")
            # 在这里可以处理网络错误，例如显示一个错误消息

    def update_graph_state(self, state):
        """更新图状态"""
        self.graph_widget.update_graph_state(state)

    def start_websocket_listener(self):
        """启动 WebSocket 监听线程"""

        def listen():

            # 确保后端服务已启动
            while not wait_for_backend():
                print("[start_websocket_listener] Retrying to connect to backend...")
            ws = create_connection("ws://localhost:8000/ws/state")
            while True:
                message = ws.recv()
                data = json.loads(message)
                if data["type"] == "state_update":
                    self.handle_state_update(data["data"])

        threading.Thread(target=listen, daemon=True).start()

    def handle_state_update(self, state):
        """处理来自 WebSocket 的状态更新"""
        print("agent graph view has Received state update:", state)
        self.messageState_updated.emit(state)