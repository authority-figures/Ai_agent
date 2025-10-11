from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QGroupBox
from PyQt5.QtCore import pyqtSignal
import json

class NodeDetailView(QWidget):
    messageState_updated = pyqtSignal(dict)  # 图状态更新信号
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("节点详情")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 节点信息组
        self.info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout(self.info_group)

        self.node_id_label = QLabel("节点ID: ")
        self.node_name_label = QLabel("节点名称: ")
        self.node_type_label = QLabel("节点类型: ")

        info_layout.addWidget(self.node_id_label)
        info_layout.addWidget(self.node_name_label)
        info_layout.addWidget(self.node_type_label)

        # 内容组
        self.content_group = QGroupBox("内容详情")
        content_layout = QVBoxLayout(self.content_group)

        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        content_layout.addWidget(self.content_edit)

        layout.addWidget(self.info_group)
        layout.addWidget(self.content_group)


    def handle_state_update(self, state):
        """处理来自 WebSocket 的状态更新"""
        print("agent graph view has Received state update:", state)
        self.messageState_updated.emit(state)

    def display_node_state(self, state):
        """显示节点状态"""
        if not state:
            return
        state_str = "\n".join([f"{key}: {value}" for key, value in state.items()])
        self.content_edit.append(f"\n[状态更新]\n{state_str}\n")
        node_name = state.get("node", "")
        node_state = state.get("state", "")
        state_content = node_state.get("content", "")
        self.node_name_label.setText(f"节点名称: {node_name if node_name else 'None'}")

        if isinstance(state_content, dict):
            # 格式化字典内容
            formatted_content = "\n".join([f"{key}: {value}" for key, value in state_content.items()])
            self.content_edit.setPlainText(formatted_content)
        else:
            self.content_edit.setPlainText(str(state_content))

    def display_node_info(self, node_info):
        """显示节点信息"""
        if not node_info:
            self.clear_display()
            return


        # 更新基本信息
        self.node_id_label.setText(f"节点ID: {node_info.get('id', '')}")
        self.node_name_label.setText(f"节点名称: {node_info.get('name', '')}")
        self.node_type_label.setText(f"节点类型: {node_info.get('type', '')}")

        # 更新内容详情
        content = node_info.get('content', '')
        if isinstance(content, dict):
            # 格式化字典内容
            formatted_content = "\n".join([f"{key}: {value}" for key, value in content.items()])
            self.content_edit.setPlainText(formatted_content)
        else:
            self.content_edit.setPlainText(str(content))

    def clear_display(self):
        """清空显示"""
        self.node_id_label.setText("节点ID: ")
        self.node_name_label.setText("节点名称: ")
        self.node_type_label.setText("节点类型: ")
        self.content_edit.clear()


# 测试入口
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    # 创建Qt应用实例
    app = QApplication(sys.argv)

    # 实例化要测试的视图
    node_view = NodeDetailView()
    node_view.setWindowTitle("节点详情视图测试")
    node_view.resize(500, 400)  # 设置窗口大小

    # 测试数据1: 完整的节点信息（包含字典类型的内容）
    test_node_1 = {
        "id": "node_12345",
        "name": "路径规划节点",
        "type": "algorithm",
        "content": {
            "算法类型": "RRT*",
            "规划精度": "high",
            "最大迭代次数": 1000,
            "障碍物检测": True
        }
    }

    # 测试数据2: 简单文本内容的节点
    test_node_2 = {
        "id": "node_67890",
        "name": "任务描述节点",
        "type": "text",
        "content": "从A点移动到B点，避开所有障碍物，移动速度不超过0.5m/s"
    }

    # 显示第一个测试节点
    node_view.display_node_info(test_node_1)

    # 显示窗口
    node_view.show()

    # 可以通过定时器切换测试数据，展示动态更新效果
    from PyQt5.QtCore import QTimer

    timer = QTimer()
    timer.timeout.connect(lambda: node_view.display_node_info(test_node_2))
    timer.start(3000)  # 3秒后切换到第二个测试节点

    # 启动应用事件循环
    sys.exit(app.exec_())