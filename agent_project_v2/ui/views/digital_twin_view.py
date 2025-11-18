# ui/views/digital_twin_view.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QHBoxLayout, QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt
from execution.physical.drivers.jakamini2.jakamini2_qt_api import Jakamini2QtApi
import asyncio
import threading


def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()  # 事件循环必须处于运行状态

class DigitalTwinView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=start_event_loop, args=(self.loop,), daemon=True)
        self.loop_thread.start()  # 启动线程，事件循环开始运行

        self.robot_api = Jakamini2QtApi()

        self.setLayout(QVBoxLayout())

        self.create_connect_group()

        # 2. 显示机器人状态区
        self.robot_status_label = QLabel("Robot Status: Not Connected")
        self.robot_status_label.setStyleSheet("color: grey;")
        self.layout().addWidget(self.robot_status_label)

        self.robot_state_label = QLabel("Current State: --")
        self.layout().addWidget(self.robot_state_label)

        # 3. 控制功能区（如移动、停止等）
        self.control_layout = QHBoxLayout()
        self.move_button = QPushButton("Move Robot", self)
        self.move_button.clicked.connect(self.move_robot)
        self.control_layout.addWidget(self.move_button)

        self.stop_button = QPushButton("Stop Robot", self)
        self.stop_button.clicked.connect(self.stop_robot)
        self.control_layout.addWidget(self.stop_button)

        self.layout().addLayout(self.control_layout)


    def create_connect_group(self):
        self.robot_connected = False
        # 1. 创建连接区 GroupBox
        self.connection_groupbox = QGroupBox("Connection Settings")
        self.connection_groupbox.setLayout(QFormLayout())

        # 2. 创建一个水平布局 (QHBoxLayout) 来组合 IP 输入框和下拉框
        ip_layout = QHBoxLayout()

        # 输入框 + 下拉框：用户可以选择 IP 或输入自定义 IP
        self.robot_ip_input = QComboBox(self)
        self.robot_ip_input.setEditable(True)  # 设置为可编辑模式
        self.robot_ip_input.addItem("192.168.100.20")
        self.robot_ip_input.addItem("192.168.1.2")
        self.robot_ip_input.addItem("192.168.1.3")
        ip_layout.addWidget(self.robot_ip_input)

        # 将组合框添加到 QGroupBox
        self.connection_groupbox.layout().addRow("IP Address:", ip_layout)

        # 4. 连接按钮
        self.connect_button = QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.connect_to_robot)
        self.connection_groupbox.layout().addRow(self.connect_button)

        # 5. 电源开关按钮
        self.power_button = QPushButton("Power On", self)
        self.power_button.clicked.connect(self.toggle_power)
        self.connection_groupbox.layout().addRow(self.power_button)

        # 6. 启用/禁用按钮
        self.enable_button = QPushButton("Enable", self)
        self.enable_button.clicked.connect(self.toggle_enable)
        self.connection_groupbox.layout().addRow(self.enable_button)

        # 将连接设置放在界面最上方且靠左
        self.layout().addWidget(self.connection_groupbox)

        # 初始状态下禁用电源和启用按钮
        self.power_button.setEnabled(False)
        self.enable_button.setEnabled(False)

    def connect_to_robot(self):
        ip_address = self.robot_ip_input.currentText()
        if ip_address:
            if not self.robot_connected:
                # 仅提交连接任务，不阻塞，通过回调更新结果
                self.try_connect_to_robot(ip_address)
                # 临时显示"连接中..."状态
                self.connect_button.setText("Connecting...")
                self.connect_button.setStyleSheet("background-color: yellow;")
                self.connect_button.setEnabled(False)
                self.robot_status_label.setText(f"Robot Status: Connecting to {ip_address}...")
            else:
                # 断开连接逻辑（同步操作，直接执行）
                self.disconnect_robot()
        else:
            print("Invalid IP address!")
            self.robot_status_label.setText("Robot Status: Invalid IP")

    def try_connect_to_robot(self, ip: str):
        """提交异步连接任务，并注册回调函数"""
        try:
            print(f"Attempting to connect to robot at {ip}")
            # 提交协程到事件循环，获取Future对象
            future = asyncio.run_coroutine_threadsafe(self.robot_api.connect(ip), self.loop)
            # 注册连接完成后的回调函数（关键：通过回调处理结果）
            future.add_done_callback(lambda f: self.on_connect_done(f, ip))
        except Exception as e:
            print(f"Failed to submit connect task: {e}")
            self.update_ui_on_failure()

    def on_connect_done(self, future, ip):
        """连接完成后的回调函数（处理结果并更新UI）"""
        try:
            # 获取异步连接的返回结果
            result = future.result()
            # 根据连接结果判断（假设成功时result无error字段）
            if result.get("status") == "success":
                self.connect_button.setEnabled(True)
                self.robot_connected = True
                # 更新UI为"已连接"状态
                self.connect_button.setText("Disconnect")
                self.connect_button.setStyleSheet("background-color: green;")
                self.robot_status_label.setText(f"Robot Status: Connected to {ip}")
                print(f"Connected to robot at {ip}")

                self.power_button.setEnabled(True)
                self.enable_button.setEnabled(True)

            else:
                # 连接失败（如API返回错误）
                self.update_ui_on_failure()
        except Exception as e:
            # 连接过程中发生异常（如超时、网络错误）
            print(f"Connection failed: {e}")
            self.update_ui_on_failure()

    def disconnect_robot(self):
        """断开连接逻辑（如果有异步断开方法，同样用回调处理）"""
        self.robot_connected = False
        self.connect_button.setText("Connect")
        self.connect_button.setStyleSheet("background-color: lightgray;")
        self.robot_status_label.setText("Robot Status: Not Connected")
        print("Disconnected from robot")

    def update_ui_on_failure(self):
        """连接失败时统一更新UI"""
        self.connect_button.setEnabled(True)
        self.robot_connected = False
        self.connect_button.setText("Connect")
        self.connect_button.setStyleSheet("background-color: red;")



    def toggle_power(self):
        # 切换电源状态
        if self.power_button.text() == "Power On":
            self.power_button.setText("Power Off")
            self.power_button.setStyleSheet("background-color: green;")
            self.robot_state_label.setText("Power: On")
            print("Power On")
        else:
            self.power_button.setText("Power On")
            self.power_button.setStyleSheet("background-color: lightgray;")
            self.robot_state_label.setText("Power: Off")
            print("Power Off")

    def toggle_enable(self):
        # 启用/禁用状态切换
        if self.enable_button.text() == "Enable":
            self.enable_button.setText("Disable")
            self.enable_button.setStyleSheet("background-color: green;")
            self.robot_state_label.setText("Status: Enabled")
            print("Robot Enabled")
        else:
            self.enable_button.setText("Enable")
            self.enable_button.setStyleSheet("background-color: lightgray;")
            self.robot_state_label.setText("Status: Disabled")
            print("Robot Disabled")

    def switch_control_mode(self):
        # 这里做控制模式切换，假设是仿真模式 / 物理模式切换
        print("Switching to control mode...")
        # 你可以根据是否连接成功来切换操作模式
        if self.robot_connected:
            self.robot_state_label.setText("Current State: Control Mode Activated")
        else:
            self.robot_state_label.setText("Current State: Not Connected")

    def move_robot(self):
        # 触发机器人移动命令的逻辑
        print("Moving the robot...")
        # 在这里通过控制指令让机器人移动

    def stop_robot(self):
        # 停止机器人运动的逻辑
        print("Stopping the robot...")
        # 在这里通过控制指令让机器人停止



if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 创建一个 QMainWindow 来容纳 DigitalTwinView
    main_window = QMainWindow()
    main_window.setWindowTitle("Digital Twin View Test")

    # 初始化 DigitalTwinView 作为一个中心部件
    digital_twin_view = DigitalTwinView()

    # 将 DigitalTwinView 设置为 main window 的中心部件
    main_window.setCentralWidget(digital_twin_view)

    # 设置主窗口大小并展示
    main_window.setGeometry(100, 100, 800, 600)
    main_window.show()

    sys.exit(app.exec_())  # 启动事件循环
    pass