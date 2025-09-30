import sys
from PyQt5.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout, QApplication, QVBoxLayout, QLabel, QTextEdit, \
    QGroupBox
from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont


# 模拟服务定位器
class ServiceLocator:
    _services = {}

    @classmethod
    def register(cls, service_name, service_instance):
        cls._services[service_name] = service_instance

    @classmethod
    def get(cls, service_name):
        return cls._services.get(service_name)


# 模拟事件总线
class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event_type, data):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)


# 模拟 AgentService
class AgentService:
    def get_graph_structure(self):
        """返回测试图结构"""
        return {
            'nodes': [
                {'id': 'start', 'name': '开始', 'type': 'input'},
                {'id': 'plan', 'name': '规划', 'type': 'process'},
                {'id': 'decision', 'name': '决策', 'type': 'process'},
                {'id': 'execute', 'name': '执行', 'type': 'action'},
                {'id': 'evaluate', 'name': '评估', 'type': 'process'},
                {'id': 'end', 'name': '结束', 'type': 'output'}
            ],
            'edges': [
                {'from': 'start', 'to': 'plan'},
                {'from': 'plan', 'to': 'decision'},
                {'from': 'decision', 'to': 'execute'},
                {'from': 'execute', 'to': 'evaluate'},
                {'from': 'evaluate', 'to': 'end'}
            ]
        }

    def get_node_info(self, node_id):
        """返回节点信息"""
        if node_id == 'plan':
            return {
                'id': 'plan',
                'name': '规划',
                'type': 'process',
                'content': {
                    'plan_id': 'plan_123',
                    'status': 'completed',
                    'steps': ['移动到位姿A', '抓取物体', '移动到目标位置'],
                    'created_at': '2023-10-15T14:30:00'
                }
            }
        elif node_id == 'execute':
            return {
                'id': 'execute',
                'name': '执行',
                'type': 'action',
                'content': {
                    'action_id': 'action_456',
                    'status': 'in_progress',
                    'command': 'move_to_position',
                    'parameters': {'x': 0.5, 'y': 0.2, 'z': 0.3},
                    'started_at': '2023-10-15T14:32:00'
                }
            }
        else:
            return {
                'id': node_id,
                'name': node_id.capitalize(),
                'type': 'node',
                'content': f'这是 {node_id} 节点的详细信息'
            }


# 图节点类
class GraphNode:
    def __init__(self, node_id, name, pos, width=120, height=60):
        self.node_id = node_id
        self.name = name
        self.pos = QPointF(pos[0], pos[1])  # 使用 QPointF 对象
        self.width = width
        self.height = height
        self.is_current = False

    def set_current(self, is_current):
        self.is_current = is_current

    def contains_point(self, point):
        """检查点是否在节点内"""
        x, y = point.x(), point.y()
        return (self.pos.x() <= x <= self.pos.x() + self.width and
                self.pos.y() <= y <= self.pos.y() + self.height)


# 图组件
class GraphWidget(QWidget):
    node_selected = pyqtSignal(str)

    def __init__(self, graph_structure):
        super().__init__()
        self.graph_structure = graph_structure
        self.nodes = {}
        self.current_node = None
        self.setMinimumSize(600, 400)

        # 创建节点
        self.create_nodes()

    def create_nodes(self):
        """创建节点"""
        for i, node in enumerate(self.graph_structure['nodes']):
            pos = (i * 150, 100)  # 位置元组
            self.nodes[node['id']] = GraphNode(node['id'], node['name'], pos)

    def paintEvent(self, event):
        """绘制图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制边
        painter.setPen(QPen(Qt.black, 2))
        for edge in self.graph_structure['edges']:
            start_node = self.nodes[edge['from']]
            end_node = self.nodes[edge['to']]

            start_x = start_node.pos.x() + start_node.width / 2
            start_y = start_node.pos.y() + start_node.height
            end_x = end_node.pos.x() + end_node.width / 2
            end_y = end_node.pos.y()

            # 将浮点数转换为整数
            painter.drawLine(
                int(start_x), int(start_y),
                int(end_x), int(end_y)
            )

        # 绘制节点
        font = QFont("Arial", 10)
        painter.setFont(font)

        for node_id, node in self.nodes.items():
            # 设置节点颜色
            if node.is_current:
                painter.setBrush(QBrush(QColor(255, 200, 200)))  # 当前节点为红色
            else:
                painter.setBrush(QBrush(QColor(200, 220, 255)))  # 其他节点为蓝色

            # 绘制节点矩形
            painter.setPen(QPen(Qt.black, 2))
            painter.drawRect(
                int(node.pos.x()), int(node.pos.y()),
                int(node.width), int(node.height)
            )

            # 绘制节点文本
            text_rect = painter.fontMetrics().boundingRect(node.name)
            text_x = int(node.pos.x() + (node.width - text_rect.width()) / 2)
            text_y = int(node.pos.y() + (node.height + text_rect.height()) / 2 - 5)
            painter.drawText(text_x, text_y, node.name)

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        pos = event.pos()
        for node_id, node in self.nodes.items():
            if node.contains_point(pos):
                self.node_selected.emit(node_id)
                break

    def update_graph_state(self, state):
        """更新图状态"""
        current_node_id = state.get('current_node')
        if current_node_id:
            # 重置所有节点状态
            for node in self.nodes.values():
                node.set_current(False)

            # 设置当前节点
            if current_node_id in self.nodes:
                self.nodes[current_node_id].set_current(True)
                self.current_node = current_node_id

            # 重绘
            self.update()


# 节点详情视图
class NodeDetailView(QWidget):
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


# 对话历史视图
class ChatHistoryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("对话历史")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 聊天历史文本框
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

    def add_message(self, message):
        """添加新消息到聊天历史"""
        # 格式化消息
        formatted_message = f"<b>[{message.get('timestamp', '')}] {message.get('sender', '')}:</b> "
        formatted_message += f"{message.get('content', '')}<br>"

        # 添加到文本框
        self.chat_history.append(formatted_message)

        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )


# Agent工作流视图
class AgentGraphView(QWidget):
    node_selected = pyqtSignal(str)  # 转发信号

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("Agent工作流程")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 获取Agent图结构
        agent_service = ServiceLocator.get('agent_service')
        graph_structure = agent_service.get_graph_structure()

        # 创建图组件
        self.graph_widget = GraphWidget(graph_structure)
        layout.addWidget(self.graph_widget)

        # 连接信号
        self.graph_widget.node_selected.connect(self.node_selected.emit)

    def update_graph_state(self, state):
        """更新图状态"""
        self.graph_widget.update_graph_state(state)


# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Robot Control System")
        self.setGeometry(100, 100, 1600, 900)

        # 创建主分割器（左右布局）
        main_splitter = QSplitter(Qt.Horizontal)

        # 右侧：Agent工作区（垂直分割）
        right_splitter = QSplitter(Qt.Vertical)

        # 右侧上部：Agent工作流视图（占50%高度）
        self.agent_graph_view = AgentGraphView()
        right_splitter.addWidget(self.agent_graph_view)

        # 右侧下部：详细信息区（垂直分割）
        bottom_splitter = QSplitter(Qt.Vertical)

        # 节点详情视图（占30%高度）
        self.node_detail_view = NodeDetailView()
        bottom_splitter.addWidget(self.node_detail_view)

        # 对话历史视图（占70%高度）
        self.chat_history_view = ChatHistoryView()
        bottom_splitter.addWidget(self.chat_history_view)

        right_splitter.addWidget(bottom_splitter)
        right_splitter.setStretchFactor(0, 5)  # 上部占50%
        right_splitter.setStretchFactor(1, 5)  # 下部占50%

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 4)  # 右侧占40%

        self.setCentralWidget(main_splitter)

        # 连接信号
        self.agent_graph_view.node_selected.connect(self.on_node_selected)

        # 初始化事件总线
        self.event_bus = EventBus()
        ServiceLocator.register('event_bus', self.event_bus)

        # 订阅事件
        self.event_bus.subscribe('agent_state_update', self.on_agent_update)
        self.event_bus.subscribe('chat_message', self.on_chat_message)

    def on_node_selected(self, node_id):
        """处理节点选择事件"""
        agent_service = ServiceLocator.get('agent_service')
        node_info = agent_service.get_node_info(node_id)
        self.node_detail_view.display_node_info(node_info)

    def on_agent_update(self, state):
        """更新Agent状态"""
        self.agent_graph_view.update_graph_state(state)

    def on_chat_message(self, message):
        """添加新聊天消息"""
        self.chat_history_view.add_message(message)


if __name__ == "__main__":
    # 创建Qt应用实例
    app = QApplication(sys.argv)

    # 初始化服务定位器
    agent_service = AgentService()
    ServiceLocator.register('agent_service', agent_service)

    # 创建主窗口实例
    window = MainWindow()

    # 添加测试数据
    test_messages = [
        {
            "timestamp": "10:00:00",
            "sender": "用户",
            "content": "你好，系统准备好了吗？"
        },
        {
            "timestamp": "10:00:05",
            "sender": "系统",
            "content": "已准备就绪，可以开始执行任务"
        },
        {
            "timestamp": "10:00:15",
            "sender": "用户",
            "content": "请展示一下可用的节点"
        }
    ]

    # 向聊天历史添加测试消息
    for msg in test_messages:
        window.on_chat_message(msg)


    # 模拟Agent状态更新
    def update_agent_state():
        # 获取事件总线
        event_bus = ServiceLocator.get('event_bus')

        # 模拟状态更新
        states = [
            {"current_node": "start"},
            {"current_node": "plan"},
            {"current_node": "decision"},
            {"current_node": "execute"},
            {"current_node": "evaluate"},
            {"current_node": "end"}
        ]

        current_index = 0

        def send_next_state():
            nonlocal current_index
            if current_index < len(states):
                state = states[current_index]
                event_bus.publish('agent_state_update', state)
                current_index += 1
                QTimer.singleShot(1000, send_next_state)  # 1秒后发送下一个状态

        send_next_state()


    # 启动状态更新
    QTimer.singleShot(1000, update_agent_state)

    # 显示窗口
    window.show()

    # 启动应用事件循环
    sys.exit(app.exec_())