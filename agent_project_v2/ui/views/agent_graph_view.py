from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, QTimer
from agent_project_v2.ui.widgets.graph_widget import GraphWidget
import requests

class AgentGraphView(QWidget):
    node_selected = pyqtSignal(str)  # 转发信号

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("Agent工作流程")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # # 获取Agent图结构
        # agent_service = ServiceLocator.get('agent_service')
        # graph_structure = agent_service.get_graph_structure()

        # 创建图组件
        self.graph_widget = GraphWidget({}) # 暂时传入空图，后续可以通过update_graph_state更新
        layout.addWidget(self.graph_widget)

        # 指定延迟时间后，执行一次特定的函数 / 槽函数
        QTimer.singleShot(1000, self.fetch_graph_data)

        # 连接信号
        self.graph_widget.node_selected.connect(self.node_selected.emit)

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