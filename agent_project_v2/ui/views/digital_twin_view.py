# ui/views/digital_twin_view.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QHBoxLayout, QGroupBox, QFormLayout, QComboBox
, QGridLayout
)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
from execution.physical.drivers.jakamini2.jakamini2_qt_api import Jakamini2QtApi
import asyncio
import threading
# from ui.views.simulation_view import PyBulletEmbedder
from execution.digital_twin.digital_twin_process import DigitalTwinProcess,CustomDigitalTwinEnv
from ui.widgets.robot_state_widget import *
from ui.widgets.DT_debug_widget import RobotDebugWidget
import Xlib
import Xlib.display
from Xlib import X
import subprocess
import time
import websockets
import json
import numpy as np

class PyBulletEmbedder:
    """PyBullet窗口嵌入工具类"""

    def __init__(self, container_widget,window_title:str="PyBulletDT"):
        self.container = container_widget
        self.window_title = window_title
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.bullet_window_id = None
        self.container_window_id = int(container_widget.winId())

    def find_pybullet_window(self):
        """查找PyBullet窗口"""
        # 首先尝试使用xdotool查找窗口
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", self.window_title],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                window_ids = result.stdout.strip().split('\n')
                return int(window_ids[0])

            # 如果找不到，尝试查找其他可能的PyBullet窗口
            result = subprocess.run(
                ["xdotool", "search", "--name", "Bullet Physics"],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                window_ids = result.stdout.strip().split('\n')
                return int(window_ids[-1])

        except Exception as e:
            print(f"使用xdotool查找窗口时出错: {e}")

        # 如果xdotool失败，回退到Xlib方法
        windows = self.root.query_tree().children

        for window in windows:
            try:
                name = window.get_wm_name()
                if name and self.window_title in name:
                    print(f"找到PyBullet窗口: {name}")
                    return window.id
                elif name and "Bullet Physics" in name:
                    print(f"找到可能的PyBullet窗口: {name}")
                    return window.id
            except Xlib.error.BadWindow:
                continue
            except Xlib.error.BadMatch:
                continue

        print("未找到PyBullet窗口")
        return None

    def embed_window(self):
        """嵌入PyBullet窗口"""
        if not self.bullet_window_id:
            self.bullet_window_id = self.find_pybullet_window()

        if self.bullet_window_id:
            try:
                # 首先隐藏窗口
                subprocess.run(
                    ["xdotool", "windowunmap", str(self.bullet_window_id)],
                    timeout=5
                )

                # 等待一段时间确保窗口已隐藏
                time.sleep(0.1)

                # 获取PyBullet窗口对象
                bullet_window = self.display.create_resource_object('window', self.bullet_window_id)

                # 设置窗口属性
                bullet_window.change_attributes(override_redirect=1)  # 关键：避免窗口管理器干预

                # 重新设置父窗口
                bullet_window.reparent(self.container_window_id, 0, 0)

                # 映射窗口（显示）
                bullet_window.map()

                # 刷新更改
                self.display.flush()

                # 调整窗口大小和位置
                self.update_window_position()

                return True
            except Exception as e:
                print(f"嵌入窗口时出错: {e}")
                return False
        return False

    def update_window_position(self):
        """更新PyBullet窗口的位置和大小"""
        if self.bullet_window_id:
            try:
                # 调整PyBullet窗口大小和位置
                bullet_window = self.display.create_resource_object('window', self.bullet_window_id)
                bullet_window.configure(
                    x=0,  # 相对于容器的x位置
                    y=0,  # 相对于容器的y位置
                    width=self.container.width(),
                    height=self.container.height()
                )
                self.display.flush()
                return True
            except Exception as e:
                print(f"调整窗口位置时出错: {e}")
                return False
        return False

    def restore_window(self):
        """恢复PyBullet窗口到原始状态"""
        if self.bullet_window_id:
            try:
                bullet_window = self.display.create_resource_object('window', self.bullet_window_id)
                bullet_window.reparent(self.root.id, 0, 0)
                self.display.flush()
                return True
            except Exception as e:
                print(f"恢复窗口时出错: {e}")
                return False
        return False

    def close(self):
        """关闭显示连接"""
        self.display.close()




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

        self.create_DT_Widget()

        self.create_status_display()

        self.create_machine_tcp_group()







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

        # 4. 连接按钮
        self.connect_button = QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.connect_to_robot)
        ip_layout.addWidget(self.connect_button)

        # 将组合框添加到 QGroupBox
        self.connection_groupbox.layout().addRow("IP Address:", ip_layout)


        # 电源与启用按钮放在一行
        button_row1 = QHBoxLayout()
        # 5. 电源开关按钮
        self.power_button = QPushButton("Power On", self)
        self.power_button.clicked.connect(self.toggle_power)
        button_row1.addWidget(self.power_button)


        # 6. 启用/禁用按钮
        self.enable_button = QPushButton("Enable", self)
        self.enable_button.clicked.connect(self.toggle_enable)
        button_row1.addWidget(self.enable_button)
        self.connection_groupbox.layout().addRow(button_row1)

        # 订阅和 debug 按钮放在一行
        button_row2 = QHBoxLayout()
        # 7. 订阅机械臂状态按钮
        self.subscribe_status_button = QPushButton("Subscribe Robot Status", self)
        self.subscribe_status_button.clicked.connect(self.toggle_subscribe)
        button_row2.addWidget(self.subscribe_status_button)

        # 8. 打开debug窗口按钮
        self.debug_button =QPushButton("Open Debug Window",self)
        if hasattr(self.parent(), 'simulation_view'):
            self.debug_widget = RobotDebugWidget(self.parent().simulation_view,self)
        else:
            print("[DT View:create_connect_group] Warning: parent has no simulation_view attribute, debug window may not work properly.")
        self.debug_button.clicked.connect(self.on_debug_button_clicked)
        button_row2.addWidget(self.debug_button)
        self.connection_groupbox.layout().addRow(button_row2)

        # 将连接设置放在界面最上方且靠左
        self.layout().addWidget(self.connection_groupbox)

        # 初始状态下禁用电源和启用按钮
        self.power_button.setEnabled(False)
        self.enable_button.setEnabled(False)

    def create_machine_tcp_group(self):
        self.machine_tcp_groupbox = QGroupBox("Machine TCP Subscription")
        self.machine_tcp_groupbox.setLayout(QFormLayout())

        tcp_layout = QHBoxLayout()
        self.machine_tcp_ip_input = QComboBox(self)
        self.machine_tcp_ip_input.setEditable(True)
        self.machine_tcp_ip_input.addItem("127.0.0.1")
        self.machine_tcp_ip_input.addItem("0.0.0.0")
        tcp_layout.addWidget(self.machine_tcp_ip_input)

        self.machine_tcp_port_input = QLineEdit(self)
        self.machine_tcp_port_input.setText("9101")
        self.machine_tcp_port_input.setMaximumWidth(80)
        tcp_layout.addWidget(self.machine_tcp_port_input)

        self.machine_tcp_start_button = QPushButton("Start TCP", self)
        self.machine_tcp_start_button.clicked.connect(self.start_machine_tcp_subscription)
        tcp_layout.addWidget(self.machine_tcp_start_button)

        self.machine_tcp_stop_button = QPushButton("Stop TCP", self)
        self.machine_tcp_stop_button.clicked.connect(self.stop_machine_tcp_subscription)
        self.machine_tcp_stop_button.setEnabled(False)
        tcp_layout.addWidget(self.machine_tcp_stop_button)

        self.machine_tcp_groupbox.layout().addRow("IP / Port:", tcp_layout)

        self.machine_tcp_status_label = QLabel("TCP server not started")
        self.machine_tcp_groupbox.layout().addRow("TCP Status:", self.machine_tcp_status_label)

        axis_grid = QGridLayout()
        self.machine_axis_labels = {}
        for col, axis in enumerate(["A", "C", "X", "Y", "Z"]):
            axis_grid.addWidget(QLabel(axis), 0, col)
            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("border: 1px solid #ced4da; padding: 4px; background-color: #ffffff;")
            self.machine_axis_labels[axis] = value_label
            axis_grid.addWidget(value_label, 1, col)

        axis_widget = QWidget(self)
        axis_widget.setLayout(axis_grid)
        self.machine_tcp_groupbox.layout().addRow("ACXYZ:", axis_widget)
        self.layout().addWidget(self.machine_tcp_groupbox)



    def create_DT_Widget(self):
        # ==============================================
        # PyBullet容器：弱化内部边框，突出全局边界
        # ==============================================

        # 启动PyBullet DT
        self.digital_twin_process = DigitalTwinProcess()
        self.digital_twin_process.start()
        self.env_loop = self.digital_twin_process.loop


        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 内部容器仅加浅边框（避免与全局边界冲突），聚焦全局区分
        self.container.setStyleSheet("""
                            QWidget {
                                border: 1px solid #ced4da;
                                border-radius: 6px;
                                background-color: grey;
                                padding: 5px;
                            }
                        """)

        self.layout().addWidget(self.container)

        # 确保容器窗口已创建
        self.container.winId()
        self.container.show()

        self.embedder = PyBulletEmbedder(self.container, self.digital_twin_process.env_title)

        self.activate_DT_button = QPushButton("Activate Digital Twin View", self)
        self.activate_DT_button.setEnabled(True)
        self.container.setLayout(QVBoxLayout())
        self.container.layout().addWidget(self.activate_DT_button)

        self.activate_DT_button.clicked.connect(self.find_DT_window)


    def create_status_display(self):

        self._last_robot_status_raw = None  # 原始列表
        self._last_robot_status_dict = None  # 解析后的 dict


        # ===== 2. 机器人状态简略区 =====
        self.status_group = QGroupBox("Robot Status", self)
        status_layout = QFormLayout(self.status_group)

        self.lbl_errcode = QLabel("--")
        self.lbl_powered = QLabel("--")
        self.lbl_enabled = QLabel("--")
        self.lbl_inpos = QLabel("--")
        self.lbl_rapidrate = QLabel("--")
        self.lbl_protective = QLabel("--")
        self.lbl_emergency = QLabel("--")

        status_layout.addRow("ErrCode:", self.lbl_errcode)
        status_layout.addRow("Powered On:", self.lbl_powered)
        status_layout.addRow("Enabled:", self.lbl_enabled)
        status_layout.addRow("In Position:", self.lbl_inpos)
        status_layout.addRow("Rapid Rate:", self.lbl_rapidrate)
        status_layout.addRow("Protective Stop:", self.lbl_protective)
        status_layout.addRow("Emergency Stop:", self.lbl_emergency)

        # 详情按钮
        self.btn_details = QPushButton("Details...", self)
        self.btn_details.clicked.connect(self.show_status_details)
        status_layout.addRow(self.btn_details)

        self.layout().addWidget(self.status_group)

        # ====== 2. 创建监听器 ======
        ws_url = "ws://127.0.0.1:8002/ws/robot_status"
        self.status_listener = RobotStatusListener(ws_url, self)
        self.status_listener.status_received.connect(self.update_robot_status_from_raw)
        self.status_listener.connection_lost.connect(self.on_ws_connection_lost)
        self.status_listener.connection_established.connect(self.on_ws_connection_established)


        self.machine_axis_listener = MachineAxisListener("ws://127.0.0.1:8003/ws/machinestate", self)
        self.machine_axis_listener.axis_received.connect(self.update_machine_axis_labels)
        self.machine_axis_listener.connection_lost.connect(self.on_machine_axis_connection_lost)
        self.machine_axis_listener.connection_established.connect(self.on_machine_axis_connection_established)



    def update_robot_status_from_raw(self, raw_status):
        """
        由外部（WebSocket / eventbus / driver）调用。
        raw_status 应该是长度为 24 的列表（robotstatus）。
        """
        self._last_robot_status_raw = raw_status
        self._last_robot_status_dict = parse_robot_status(raw_status)
        self._update_status_labels()

    def _update_status_labels(self):
        s = self._last_robot_status_dict
        if not s:
            return

        def yes_no(v: int) -> str:
            return "Yes" if v else "No"

        self.lbl_errcode.setText(str(s.get("errcode", "--")))
        self.lbl_powered.setText(yes_no(s.get("powered_on", 0)))
        self.lbl_enabled.setText(yes_no(s.get("enabled", 0)))
        self.lbl_inpos.setText(yes_no(s.get("inpos", 0)))
        self.lbl_rapidrate.setText(str(s.get("rapidrate", "--")))
        self.lbl_protective.setText(yes_no(s.get("protective_stop", 0)))
        self.lbl_emergency.setText(yes_no(s.get("emergency_stop", 0)))

        # 可以根据状态改变颜色，比如有错误时变红：
        if s.get("errcode", 0) != 0:
            self.lbl_errcode.setStyleSheet("color: red;")
        else:
            self.lbl_errcode.setStyleSheet("")

        if s.get("protective_stop", 0) == 1:
            self.lbl_protective.setStyleSheet("color: red;")
        else:
            self.lbl_protective.setStyleSheet("")

        if s.get("emergency_stop", 0) == 1:
            self.lbl_emergency.setStyleSheet("color: red;")
        else:
            self.lbl_emergency.setStyleSheet("")

    def show_status_details(self):
        """点击 Details... 按钮弹出详情窗口"""
        if not self._last_robot_status_dict:
            # 没有数据就不弹，或者弹个提示
            dlg = RobotStatusDialog({"info": "No robot status received yet."}, )
        else:
            dlg = RobotStatusDialog(self._last_robot_status_dict,)

        dlg.show()  # 不阻塞
        dlg.raise_()  # 置顶
        dlg.activateWindow()  # 激活焦点

        # 为了不被垃圾回收，要保存引用：
        self._details_window = dlg

    def on_ws_connection_lost(self, msg: str):
        print("[DT] WebSocket connection lost:", msg)
        # 你也可以在界面上提示，比如状态栏显示红灯

    def on_ws_connection_established(self):
        print("[DT] WebSocket connection established")
        # 可以在 UI 上显示“已连接物理服务”

    def update_machine_axis_labels(self, axis_values):
        # 转化为机床实际坐标
        A, C, X, Y, Z = axis_values
        A = np.rad2deg(A) - 2.5088
        C = np.rad2deg(C) + 342.3689
        X = X * 1000 - 768.2837999999999
        Y = Y * 1000 - 597.0038999999999
        Z = Z * 1000 + 90.13409999999999
        axis_values = [A, C, X, Y, Z]
        for axis, value in zip(["A", "C", "X", "Y", "Z"], axis_values):
            label = self.machine_axis_labels.get(axis)
            if label is not None:
                label.setText(f"{float(value):.5f}")

    def on_machine_axis_connection_lost(self, msg: str):
        print("[DT] Machine axis WebSocket connection lost:", msg)
        self.machine_tcp_status_label.setText(f"WS disconnected: {msg}")

    def on_machine_axis_connection_established(self):
        print("[DT] Machine axis WebSocket connection established")

    def start_machine_tcp_subscription(self):
        host = self.machine_tcp_ip_input.currentText().strip() or "127.0.0.1"
        port_text = self.machine_tcp_port_input.text().strip() or "9101"
        try:
            port = int(port_text)
        except ValueError:
            self.machine_tcp_status_label.setText("Invalid TCP port")
            return

        future = asyncio.run_coroutine_threadsafe(
            self.digital_twin_process.env.start_machine_axis_tcp_server(host=host, port=port),
            self.loop,
        )
        future.add_done_callback(self._on_start_machine_tcp_done)
        self.machine_tcp_status_label.setText(f"Starting TCP server at {host}:{port} ...")

    def _on_start_machine_tcp_done(self, future):
        try:
            result = future.result()
        except Exception as e:
            self.machine_tcp_status_label.setText(f"Start TCP failed: {e}")
            return

        if result.get("status") == "success":
            self.machine_tcp_status_label.setText(
                f"{result.get('message')} ({result.get('host')}:{result.get('port')})")
            self.machine_tcp_start_button.setEnabled(False)
            self.machine_tcp_stop_button.setEnabled(True)
        else:
            self.machine_tcp_status_label.setText(result.get("message", "Start TCP failed"))

    def stop_machine_tcp_subscription(self):
        future = asyncio.run_coroutine_threadsafe(
            self.digital_twin_process.env.stop_machine_axis_tcp_server(),
            self.loop,
        )
        future.add_done_callback(self._on_stop_machine_tcp_done)
        self.machine_tcp_status_label.setText("Stopping TCP server ...")

    def _on_stop_machine_tcp_done(self, future):
        try:
            result = future.result()
        except Exception as e:
            self.machine_tcp_status_label.setText(f"Stop TCP failed: {e}")
            return

        if result.get("status") == "success":
            self.machine_tcp_status_label.setText(result.get("message", "TCP server stopped"))
            self.machine_tcp_start_button.setEnabled(True)
            self.machine_tcp_stop_button.setEnabled(False)
        else:
            self.machine_tcp_status_label.setText(result.get("message", "Stop TCP failed"))


    def find_DT_window(self):
        # 初始化嵌入工具
        # 创建gui环境
        asyncio.run_coroutine_threadsafe(self.digital_twin_process.env.initialize(),self.loop)

        # 启动仿真
        asyncio.run_coroutine_threadsafe(self.digital_twin_process.env.load_scene(), self.loop)
        asyncio.run_coroutine_threadsafe(self.digital_twin_process.env.start_simulation(),self.loop)

        # 订阅机床状态
        asyncio.run_coroutine_threadsafe(self.digital_twin_process.env.subscribe_machine_state(True), self.loop)
        self.machine_axis_listener.start()


        # 设置定时器查找PyBullet窗口
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.find_and_embed_pybullet)
        self.timer.start(1000)  # 每1000毫秒检查一次，给PyBullet更多时间启动

        # 设置定时器更新窗口位置
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_window_position)
        self.update_timer.start(100)  # 每100毫秒更新一次位置

        self.connect_control_signals()
        # 仿真状态
        self.simulation_running = True

    def connect_control_signals(self):

        pass

    def find_and_embed_pybullet(self):
        """嵌入PyBullet窗口"""
        if self.embedder.embed_window():
            self.simulation_running = True
            self.timer.stop()  # 停止查找

    def update_window_position(self):
        """更新PyBullet窗口位置"""
        if self.simulation_running:
            self.embedder.update_window_position()

    def resizeEvent(self, event):
        """处理窗口大小变化"""
        super().resizeEvent(event)

        # 调整PyBullet窗口大小
        self.embedder.update_window_position()

    def moveEvent(self, event):
        """处理窗口移动事件"""
        super().moveEvent(event)

        # 更新PyBullet窗口位置
        self.embedder.update_window_position()


    def closeEvent(self, event):
        """关闭窗口时的清理工作"""
        # 停止更新定时器
        # if hasattr(self, "update_timer"):
        self.update_timer.stop()
        if hasattr(self, "machine_axis_listener"):
            self.machine_axis_listener.stop()

        # 恢复PyBullet窗口
        self.embedder.restore_window()
        self.embedder.close()

        # 停止仿真
        self.digital_twin_process.stop()
        self.digital_twin_process.wait()

        super().closeEvent(event)


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

            else:
                # 断开连接逻辑（同步操作，直接执行）
                self.disconnect_robot(ip_address)
                self.power_button.setEnabled(False)
                self.enable_button.setEnabled(False)

        else:
            print("Invalid IP address!")


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

                print(f"Connected to robot at {ip}")

                self.power_button.setEnabled(True)


                # 可以在这里直接启动，或者在“连接机器人成功”后再启动
                self.status_listener.start()    # 激活监听线程

            else:
                # 连接失败（如API返回错误）
                self.update_ui_on_failure()
        except Exception as e:
            # 连接过程中发生异常（如超时、网络错误）
            print(f"Connection failed: {e}")
            self.update_ui_on_failure()

    def disconnect_robot(self,ip:str):
        """断开连接逻辑（如果有异步断开方法，同样用回调处理）"""
        self.robot_connected = False
        self.connect_button.setText("Connect")
        self.connect_button.setStyleSheet("background-color: lightgray;")
        asyncio.run_coroutine_threadsafe(self.robot_api.disconnect(ip), self.loop)
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
            self.enable_button.setEnabled(True)
            asyncio.run_coroutine_threadsafe(self.robot_api.power_on(), self.loop)
            print("Power On")
        else:
            self.power_button.setText("Power On")
            self.power_button.setStyleSheet("background-color: lightgray;")
            self.enable_button.setEnabled(False)
            asyncio.run_coroutine_threadsafe(self.robot_api.power_off(), self.loop)
            print("Power Off")

    def toggle_enable(self):
        # 启用/禁用状态切换
        if self.enable_button.text() == "Enable":
            self.enable_button.setText("Disable")
            self.enable_button.setStyleSheet("background-color: green;")
            asyncio.run_coroutine_threadsafe(self.robot_api.enable_robot(), self.loop)
            print("Robot Enabled")
        else:
            self.enable_button.setText("Enable")
            self.enable_button.setStyleSheet("background-color: lightgray;")
            asyncio.run_coroutine_threadsafe(self.robot_api.disable_robot(), self.loop)
            print("Robot Disabled")

    def toggle_subscribe(self):
        # 订阅/取消订阅状态切换
        if self.subscribe_status_button.text() == "Subscribe Robot Status":
            self.subscribe_status_button.setText("Unsubscribe Robot Status")
            self.subscribe_status_button.setStyleSheet("background-color: green;")
            asyncio.run_coroutine_threadsafe(self.robot_api.start_subscribe(), self.loop)

            print("Subscribed to Robot Status")
        else:
            self.subscribe_status_button.setText("Subscribe Robot Status")
            self.subscribe_status_button.setStyleSheet("background-color: lightgray;")
            asyncio.run_coroutine_threadsafe(self.robot_api.stop_subscribe(), self.loop)

            print("Unsubscribed from Robot Status")

    def on_debug_button_clicked(self):
        if hasattr(self, 'debug_widget'):
            self.debug_widget.show()
            self.debug_widget.raise_()
            self.debug_widget.activateWindow()
        else:
            print("[DT View:on_debug_button_clicked] Error: debug_widget attribute not found.")



class MachineAxisListener(QObject):
    axis_received = pyqtSignal(object)
    connection_lost = pyqtSignal(str)
    connection_established = pyqtSignal()

    def __init__(self, ws_url: str, parent=None):
        super().__init__(None)
        self.ws_url = ws_url
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run_event_loop)
        self._stop_flag = False

    def start(self):
        self._stop_flag = False
        if not self._thread.isRunning():
            self._thread.start()

    def stop(self):
        self._stop_flag = True

    def _run_event_loop(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._ws_loop())
        loop.close()
        self._thread.quit()

    async def _ws_loop(self):
        try:
            async with websockets.connect(self.ws_url) as ws:
                self.connection_established.emit()
                while not self._stop_flag:
                    try:
                        msg = await ws.recv()
                    except websockets.ConnectionClosed as e:
                        self.connection_lost.emit(f"Connection closed: {e}")
                        break

                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        self.connection_lost.emit("Received invalid JSON")
                        continue

                    if data.get("status") == "success":
                        axis_values = data.get("axis_values")
                        if axis_values is not None:
                            self.axis_received.emit(axis_values)
                    await asyncio.sleep(0)
        except Exception as e:
            self.connection_lost.emit(f"WebSocket error: {e}")



class RobotStatusListener(QObject):
    """
    在独立线程中运行的 WebSocket 客户端，监听机器人状态。
    收到数据后通过 status_received 信号发回 UI 线程。
    """
    status_received = pyqtSignal(object)      # 传 raw_status（比如长度 24 的列表）
    connection_lost = pyqtSignal(str)         # 连接断开/错误信息
    connection_established = pyqtSignal()     # 首次连接成功

    def __init__(self, ws_url: str, parent=None):
        super().__init__(None)
        self.ws_url = ws_url
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run_event_loop)
        self._stop_flag = False

    def start(self):
        """启动监听线程"""
        self._stop_flag = False
        self._thread.start()

    def stop(self):
        """请求停止监听线程"""
        self._stop_flag = True

    def _run_event_loop(self):
        """在线程中创建并运行 asyncio 事件循环"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._ws_loop())
        loop.close()
        self._thread.quit()

    async def _ws_loop(self):
        """WebSocket 主循环：连接 + 收消息"""
        try:
            async with websockets.connect(self.ws_url) as ws:
                self.connection_established.emit()
                while not self._stop_flag:
                    try:
                        msg = await ws.recv()
                    except websockets.ConnectionClosed as e:
                        self.connection_lost.emit(f"Connection closed: {e}")
                        break

                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        self.connection_lost.emit("Received invalid JSON")
                        continue

                    # 这里根据你服务器发送的数据结构取出 robotstatus
                    # 你现在发的是：{"status": "ok", "data": current}
                    if data.get("status") == "ok":
                        raw_status = data.get("data")
                        # raw_status 应该是长度 24 的列表（robotstatus）
                        self.status_received.emit(raw_status)
                    # 也可以处理 "no_data" 之类的状态

                    await asyncio.sleep(0)  # 让出控制权

        except Exception as e:
            self.connection_lost.emit(f"WebSocket error: {e}")





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