import sys,os
import logging
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ))
import requests
from PyQt5.QtWidgets import QMainWindow, QSplitter, QTabWidget
from PyQt5.QtCore import Qt
from simulation_view import SimulationView

from agent_graph_view import AgentGraphView
from node_detail_view import NodeDetailView
from chat_history_view import ChatHistoryView
from agent_chat_view import AgentChatView, AgentWorker
from digital_twin_view import DigitalTwinView
from task_info_view import TaskInfoView
from ui.widgets.qt_log_handler import QtLogHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Agent Robot Control System")
        self.setGeometry(100, 100, 1600, 900)

        # 创建主分割器（左右布局）
        main_splitter = QSplitter(Qt.Horizontal)


        # ===== 左侧：标签页容器（Simulation / Digital Twin）=====
        # # 左侧：仿真视图（占60%宽度）
        self.tab_widget = QTabWidget()
        self.simulation_view = SimulationView()
        self.tab_widget.addTab(self.simulation_view, "Simulation")
        # 数字孪生视图
        self.digital_twin_view = DigitalTwinView()
        self.tab_widget.addTab(self.digital_twin_view, "Digital Twin")

        main_splitter.addWidget(self.tab_widget)
        main_splitter.setStretchFactor(0, 6)  # 6:4的比例
        # dock = QDockWidget("Simulation", self)
        # dock.setWidget(self.simulation_view)
        # self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # 右侧：Agent工作区（垂直分割）
        right_splitter = QSplitter(Qt.Vertical)

        # 右侧上部：Agent工作流视图（占50%高度）
        # 包含对话视图和节点图
        top_splitter = QSplitter(Qt.Vertical)

        self.agent_chat_view = AgentChatView()
        self.task_info_view = TaskInfoView()
        chat_task_splitter = QSplitter(Qt.Horizontal)
        chat_task_splitter.addWidget(self.agent_chat_view)
        chat_task_splitter.addWidget(self.task_info_view)
        # 设置拉伸比例
        chat_task_splitter.setStretchFactor(0, 8)  # agent_chat_view 占3份
        chat_task_splitter.setStretchFactor(1, 2)  # task_info_view 占2份
        self.task_info_view.setMinimumWidth(100)
        # top_splitter.addWidget(self.agent_chat_view)
        top_splitter.insertWidget(0,chat_task_splitter)

        self.agent_graph_view = AgentGraphView()
        agent_graph_view_splitter = QSplitter(Qt.Horizontal)
        agent_graph_view_splitter.addWidget(self.agent_graph_view)
        # 节点详情视图（占30%高度）
        self.node_detail_view = NodeDetailView()
        agent_graph_view_splitter.addWidget(self.node_detail_view)
        agent_graph_view_splitter.setStretchFactor(0, 6)
        agent_graph_view_splitter.setStretchFactor(1, 4)
        self.node_detail_view.setMinimumWidth(300)
        top_splitter.addWidget(agent_graph_view_splitter)
        top_splitter.setStretchFactor(0, 4)  # 上部占40%
        top_splitter.setStretchFactor(1, 6)  # 下部占60%
        self.agent_chat_view.setMinimumHeight(300)
        right_splitter.addWidget(top_splitter)


        # 右侧下部：详细信息区（垂直分割）
        bottom_splitter = QSplitter(Qt.Vertical)



        # 对话历史视图（占70%高度）
        self.chat_history_view = ChatHistoryView()
        bottom_splitter.addWidget(self.chat_history_view)

        right_splitter.addWidget(bottom_splitter)
        right_splitter.setStretchFactor(0, 5)  # 上部占50%
        right_splitter.setStretchFactor(1, 5)  # 下部占50%

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(1, 4)  # 右侧占40%

        self.create_log_handler()


        self.setCentralWidget(main_splitter)
        self.agent_chat_view.messageSent.connect(self.handle_agent_reply)
        # # 将图状态更新信号连接到聊天视图的槽函数（send state）
        # self.agent_graph_view.messageState_updated.connect(
        #     lambda state_dict:self.agent_chat_view.append_message("Agent", f"Agent状态更新: {state_dict}")
        # )
        # 将图状态更新信号连接到聊天视图的槽函数
        self.agent_graph_view.messageState_updated.connect(self.node_detail_view.display_node_state)
        self.agent_graph_view.messageState_updated.connect(self.node_detail_view.display_node_state)
        # 将图状态更新信号连接到节点详情视图的槽函数
        self.agent_graph_view.messageState_updated.connect(
            lambda state_dict:self.on_agent_update({**state_dict,"current_node": state_dict.get("node","")})
        )

        # 将图状态更新信号连接到agent回复函数，用于finished_task_channel信息发布
        self.agent_graph_view.messageState_updated.connect(
            lambda message_data: self.on_agent_reply(str(message_data.get('state',{}).get("content","")))
            if message_data.get("node", None) == "finished_task" else None
        )

        self.agent_graph_view.graph_widget.node_double_clicked.connect(self.node_detail_view.display_node_state)

        # 连接信号
        # self.agent_graph_view.node_selected.connect(self.on_node_selected)
        # ServiceLocator.get('event_bus').subscribe('agent_state_update', self.on_agent_update)
        # ServiceLocator.get('event_bus').subscribe('chat_message', self.on_chat_message)

    # def on_node_selected(self, node_id):
    #     """处理节点选择事件"""
    #     agent_service = ServiceLocator.get('agent_service')
    #     node_info = agent_service.get_node_info(node_id)
    #     self.node_detail_view.display_node_info(node_info)

    def create_log_handler(self):
        # 1. 创建 handler
        self.qt_handler = QtLogHandler()
        self.qt_handler.setLevel(logging.INFO)  # 需要什么级别自己调
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.qt_handler.setFormatter(formatter)

        # 2. 连接信号 -> 槽函数
        self.qt_handler.log_signal.connect(self.append_log)

        # 3. 把 handler 装到 root logger 上，这样所有 logger 都会走这里
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.qt_handler)

    def append_log(self, text: str):
        """在 Qt 界面上追加一行日志"""
        self.chat_history_view.chat_history.append(text)


    def on_agent_update(self, state):
        """更新Agent状态"""
        self.agent_graph_view.update_graph_state(state)

    def on_chat_message(self, message):
        """添加新聊天消息"""
        self.chat_history_view.add_message(message)


    # test
    def handle_agent_reply(self, text):

        # 1. 如果上一条还没跑完，直接终止它
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()  # 或 .requestInterruption() + 线程里检查
            self.worker.wait()  # 等它真的结束

        # 2. 再启动新线程
        self.worker = AgentWorker(text, self)
        self.worker.reply_ready.connect(self.on_agent_reply)
        self.worker.error_occurred.connect(self.on_agent_error)
        self.worker.start()

        # reply = f"I received: {text}"
        # self.agent_chat_view.append_message("Agent", reply)

    def on_agent_reply(self, reply):
        self.agent_chat_view.append_message("Agent", reply)

    def on_agent_error(self, err):
        self.agent_chat_view.append_message("System", f"[Error] {err}")



if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from agent.services.agent_service import AgentService
    from core.service_locator import ServiceLocator

    agent_service = AgentService()
    ServiceLocator.register('agent_service', agent_service)

    # 创建Qt应用实例
    app = QApplication(sys.argv)

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
    import time
    from PyQt5.QtCore import QTimer


    # 3秒后更新节点状态
    # def update_agent_state():
    #     window.on_agent_update({"current_node": "decision"})


    timer = QTimer()
    # timer.timeout.connect(update_agent_state)
    timer.start(3000)  # 3秒后执行

    # 显示窗口
    window.show()

    # 启动应用事件循环
    sys.exit(app.exec_())