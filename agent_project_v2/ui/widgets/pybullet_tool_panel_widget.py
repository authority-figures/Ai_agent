import json

from PyQt5.QtCore import pyqtSignal, Qt, QEvent, QThread, QTimer, QSize, QPoint
import os
from xml.etree import ElementTree as ET

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QStackedWidget, QComboBox, QLabel,
                             QLineEdit, QSizePolicy, QGroupBox, QLayout, QApplication, QSpacerItem, QFormLayout,
                             QButtonGroup, QToolButton, QFrame,QHeaderView, QTableWidget, QTableWidgetItem, QFileDialog,
                             QAction, QMenu
                             )
from PyQt5.QtGui import QIcon,QPixmap

from core.async_tools import AsyncRunner
import asyncio
import websockets
import logging
import re
from core.simulation_request import *
from ui.widgets.DT_debug_widget import PathDataDialog

colors = {
    "light_gray": "#f0f0f0",
    "dark_gray": "#A0A0A0",
    "blue": "#3333ff",
    "green": "#33cc33",
    "red": "#ff3333",
    "black": "#333333",
    "white": "#ffffff",
    "yellow": "#ffff33",
    "purple": "#9933ff",
    "orange": "#ff9900",
    "pink": "#ff99cc",
    "cyan": "#00ffff",
    "brown": "#996633",
    "gold": "#ffd700",
    "silver": "#c0c0c0",
    "navy": "#000080",
    "indigo": "#4b0082",
    "magenta": "#ff00ff",
    "teal": "#008080",
    "olive": "#808000",
    "light_blue": "#ADD8E6",
    "light_green": "#90EE90",
    "light_yellow": "#FFFFE0",
    "light_purple": "#D8BFD8",
    "light_orange": "#FFDAB9",
    "light_pink": "#FFB6C1",
    "light_cyan": "#E0FFFF",
    "light_brown": "#D2B48C",
    "light_gold": "#FAFAD2",
    "light_silver": "#C0C0C0",
    "light_navy": "#000080",
    "light_indigo": "#4B0082",
    "light_magenta": "#FF00FF",
    "light_teal": "#008080",
    "light_olive": "#808000"
}

# WebSocket 客户端
class WebSocketClient(QThread):
    joint_states_signal = pyqtSignal(list)

    def __init__(self,loop=None):
        super().__init__()
        self.loop = loop or asyncio.new_event_loop()
    async def listen(self):
        uri = "ws://127.0.0.1:8001/ws/robotstate"
        async with websockets.connect(
                uri,
                ping_interval=None,  # 不自动发 ping
                ping_timeout=None,  # 不因 ping 超时断开
        ) as websocket:
            print("[WebSocketClient] Connected to WebSocket:", uri)
            while True:
                message = await websocket.recv()  # 接收消息
                data = json.loads(message)  # 假设消息是 JSON 格式
                joints = data.get("jointstates",None)
                if joints:
                    self.joint_states_signal.emit(joints)

    def run(self):
        """ Runs the event loop in a separate thread """
        try:
            # # Check if the current thread has an event loop
            # if not asyncio.get_event_loop().is_running():
            #     loop = asyncio.new_event_loop()
            #     asyncio.set_event_loop(loop)  # Set a new event loop for this thread
            #
            # # Now you can safely call asyncio.get_event_loop() in this thread
            # loop = asyncio.get_event_loop()
            # print("[WebSocketClient] Event loop started in thread:", QThread.currentThread())
            # # Your asyncio code
            # self.loop.run_until_complete(self.listen())  # Assuming 'listen' is an async function
            loop = asyncio.new_event_loop()  # 为当前线程创建一个新的事件循环
            asyncio.set_event_loop(loop)  # 设置该线程的事件循环
            loop.run_until_complete(self.listen())  # 运行 `listen` 方法
        except Exception as e:
            print(f"Error in event loop setup: {e}")

class LineEdit(QLineEdit):
    def __init__(self, parent=None,type='output'):
        super(LineEdit, self).__init__(parent)
        self.type = type
        self.output_style = f"""
                                QLineEdit {{
                                font: bold 12px;  /* 设置字体大小 */
                                color: {colors['white']};  /* 设置文字颜色 */
                                border: 2px solid {colors['black']};  /* 设置边框 */
                                border-radius: 5px;  /* 设置边框圆角 */
                                padding: 0px;  /* 设置内边距 */
                                background-color: {colors['silver']};  /* 设置背景色 */
                                }}
                            """
        self.input_style = f"""
                                QLineEdit {{
                                font: 12px;  /* 设置字体大小 */
                                color: {colors['black']};  /* 设置文字颜色 */
                                border: 2px solid {colors['blue']};  /* 设置边框 */
                                border-radius: 5px;  /* 设置边框圆角 */
                                padding: 0px;  /* 设置内边距 */
                                background-color: {colors['white']};  /* 设置背景色 */
                                }}
                            """
        if self.type=='output':
            self.default_style = self.output_style
        elif self.type=='input':
            self.default_style = self.input_style
        else: self.default_style = "background-color: white; color: black;"
        self.hover_style = f"""border: 2px solid {colors['cyan']};  /* 设置边框 */ border-radius: 5px;  /* 设置边框圆角 */"""  # 悬停时的样式
        self.clicked_style = f"""
                                QLineEdit {{
                                font: 12px;  /* 设置字体大小 */
                                color: {colors['black']};  /* 设置文字颜色 */
                                border: 2px solid {colors['blue']};  /* 设置边框 */
                                border-radius: 5px;  /* 设置边框圆角 */
                                padding: 0px;  /* 设置内边距 */
                                background-color: {colors['light_blue']};  /* 设置背景色 */
                                }}
                            """


        self.setStyleSheet(self.default_style)
        self.installEventFilter(self)
        self.clicked = False

    def eventFilter(self, obj, event):
        if obj == self and self.type=='input':  # 只有input才响应鼠标状态
            if event.type() == QEvent.MouseButtonPress:
                self.setStyleSheet(self.clicked_style)
                self.setFocus()  # 确保获取焦点以进入编辑状态
            elif event.type() == QEvent.HoverEnter and not self.hasFocus():
                self.setStyleSheet(self.hover_style)
            elif event.type() == QEvent.HoverLeave and not self.hasFocus():
                self.setStyleSheet(self.default_style)
        return super(LineEdit, self).eventFilter(obj, event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setStyleSheet(self.clicked_style)  # 获取焦点时设置为点击样式

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setStyleSheet(self.default_style)  # 失去焦点时恢复默认样式

class ArmToolPage(QWidget):
    """机械臂工具页面"""
    show_tcp_axis_changed = pyqtSignal(bool)
    tcp_pos_and_ori = pyqtSignal(dict, dict)
    end_effector_pos_and_ori = pyqtSignal(dict, dict)
    subscribe_changed = pyqtSignal(bool)
    def __init__(self, parent=None, simulation_view=None):
        super().__init__(parent)
        self.simulation_view = simulation_view

        layout = QHBoxLayout(self)

        button_layout = QVBoxLayout()

        # 创建按钮
        self.get_tcp_btn = QPushButton("获取机械臂TCP坐标")
        self.get_end_effector_btn = QPushButton("获取机械臂末端关节坐标")
        self.show_tcp_axis_btn = QPushButton("显示TCP坐标轴")
        self.subscribe_btn = QPushButton("订阅机械臂状态")
        self.synchronize_DT_btn = QPushButton("同步数字孪生状态")


        # 坐标信息显示窗口
        self.coord_display_widget = QWidget(self)
        self.coord_display_layout = QVBoxLayout(self.coord_display_widget)
        self.coord_display_layout.setAlignment(Qt.AlignTop)
        self.coord_display_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距

        # 参考系选择下拉按钮
        self.reference_frame_combo = QComboBox(self)
        self.reference_frame_combo.addItem("机械臂基座坐标系")
        self.reference_frame_combo.addItem("世界坐标系")
        self.reference_frame_combo.addItem("机床转台中心坐标系")
        # self.reference_frame_combo.currentIndexChanged.connect(self.on_reference_frame_changed)
        self.reference_frame_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                padding: 2px;
                background-color: #ffffff;  /* 默认背景色 */
                border: 1px solid #ced4da;
                border-radius: 4px;
            }

            QComboBox::drop-down {
                border: 0px;
                background-color: #f1f1f1;
            }

            QComboBox::down-arrow {
                image: url(':/resources/down-arrow.png'); /* 自定义箭头图标，如果有需要的话 */
            }

            /* 设置选中项的背景和文字颜色 */
            QComboBox::item:selected {
                background-color: #007bff;  /* 选中时的背景色（蓝色） */
                color: white;  /* 选中时文字颜色（白色） */
            }

            /* 鼠标悬停项 */
            QComboBox::item:hover {
                background-color: #0056b3;  /* 悬停时的背景色（深蓝色） */
                color: white;  /* 悬停时文字颜色（白色） */
            }
        """)

        self.create_GUI_robot_info()




        # # 添加坐标显示到布局
        self.coord_display_layout.addWidget(self.reference_frame_combo)
        self.coord_display_layout.addWidget(self.GUI_robot_info_group_box)
        # 通过 addStretch(0) 确保不留空隙
        self.coord_display_layout.addStretch(0)
        # self.coord_display_layout.addWidget(self.xyz_label)
        # self.coord_display_layout.addWidget(self.xyz_edit)
        # self.coord_display_layout.addWidget(self.quaternion_label)
        # self.coord_display_layout.addWidget(self.quaternion_edit)

        # 布局管理
        button_layout.addWidget(self.get_tcp_btn)
        button_layout.addWidget(self.get_end_effector_btn)
        button_layout.addWidget(self.show_tcp_axis_btn)
        button_layout.addWidget(self.subscribe_btn)
        button_layout.addWidget(self.synchronize_DT_btn)
        layout.addLayout(button_layout)
        layout.addWidget(self.coord_display_widget)




        # 设置显示区域的样式
        self.coord_display_widget.setStyleSheet("""
                    QWidget {
                        border: 1px solid #ced4da;
                        border-radius: 8px;
                        padding: 2px;
                        background-color: #f8f9fa;
                        min-width: 250px;  # 设置最小宽度
                    }
                    QLabel {
                        font-size: 14px;
                        color: #333;
                    }
                    QLineEdit {
                        font-size: 14px;
                        padding: 5px;
                        margin-top: 5px;
                        background-color: #ffffff;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        text-align: center;  # 使文本居中
                    }
                """)

        # 创建 WebSocket 客户端实例
        self.websocket_client = WebSocketClient(loop=self.simulation_view.pybullet_process.loop)
        # 启动 WebSocket 客户端 用于监听来自仿真环境的机械臂关节状态更新
        self.websocket_client.start()


        self.create_button_connection()
        self.create_signal_connection()



    def create_button_connection(self):
        self.reference_frame_combo.currentIndexChanged.connect(self.on_reference_frame_changed)
        self.get_tcp_btn.clicked.connect(self.on_get_tcp_btn_clicked)
        self.get_end_effector_btn.clicked.connect(self.on_get_robot_end_effector_btn_clicked)
        self.show_tcp_axis_btn.clicked.connect(self.on_show_tcp_axis_btn_clicked)
        self.subscribe_btn.clicked.connect(self.on_subscribe_btn_clicked)
        # 点击同步DT按钮后的操作
        self.synchronize_DT_btn.clicked.connect(self.on_synchronize_DT_btn_clicked)
        # 负责执行获取仿真环境机械臂数据的任务
        self.async_runner_for_synchronize_digital_twin_state = AsyncRunner(self)
        self.async_runner_for_synchronize_digital_twin_state.finished.connect(self.handle_synchronize_DT_result)

        # copy button
        self.GUI_copy_pos_btn.clicked.connect(self.copy_data)
        self.GUI_copy_ori_btn.clicked.connect(self.copy_data)
        self.GUI_copy_joints_angle_btn.clicked.connect(self.copy_data)
        self.GUI_set_pos_btn.clicked.connect(self.on_set_robot_data)
        self.GUI_set_ori_btn.clicked.connect(self.on_set_robot_data)
        self.GUI_set_joints_angle_btn.clicked.connect(self.on_set_robot_joint_data)

        pass

    def create_signal_connection(self):
        self.show_tcp_axis_changed.connect(self.on_show_axis_changed)
        self.tcp_pos_and_ori.connect(self.update_coord_display)
        self.end_effector_pos_and_ori.connect(self.update_coord_display)
        self.subscribe_changed.connect(self.on_subscribe_changed)
        self.websocket_client.joint_states_signal.connect(self.update_joint_angles_display)

    def on_reference_frame_changed(self, index):
        """参考系选择变化时更新self.simulation_view.pybullet_process.env.reference_frame"""

        # 获取选中的项
        selected_item = self.reference_frame_combo.currentText()

        # 根据选中的项设置 reference_frame
        if selected_item == "机械臂基座坐标系":
            self.simulation_view.pybullet_process.env.reference_frame = "body"
        elif selected_item == "世界坐标系":
            self.simulation_view.pybullet_process.env.reference_frame = "world"
        elif selected_item == "机床转台中心坐标系":
            self.simulation_view.pybullet_process.env.reference_frame = "CNC_C"

    def create_GUI_robot_info(self):
        # 创建显示数据的组
        self.GUI_robot_info_group_box = QGroupBox("")
        self.GUI_robot_info_group_box.setMaximumWidth(800)  # 设置最大宽度，确保显示区域不太宽
        self.GUI_data_layout = QVBoxLayout(self.GUI_robot_info_group_box)

        # 创建坐标显示区域
        self.GUI_pos_layout = QHBoxLayout()   # label copy set 水平布局
        self.GUI_pos_data_layout = QHBoxLayout()  # data set_data 水平布局
        self.GUI_pos_label = QLabel("Position:")
        self.GUI_pos_data = LineEdit(type='output')
        self.GUI_set_pos_data = LineEdit(type='input')
        self.GUI_set_pos_data.setObjectName('GUI_pos_data')
        self.GUI_pos_data.setReadOnly(True)
        self.GUI_pos_data.setFocusPolicy(Qt.NoFocus)
        self.GUI_copy_pos_btn = QPushButton("Copy")
        self.GUI_copy_pos_btn.line_edit = self.GUI_pos_data
        self.GUI_set_pos_btn = QPushButton("Set")
        self.GUI_set_pos_btn.line_edit = self.GUI_set_pos_data
        self.GUI_pos_layout.addWidget(self.GUI_pos_label)
        self.GUI_pos_layout.addWidget(self.GUI_copy_pos_btn)
        self.GUI_pos_layout.addWidget(self.GUI_set_pos_btn)
        self.GUI_pos_data_layout.addWidget(self.GUI_pos_data)
        self.GUI_pos_data_layout.addWidget(self.GUI_set_pos_data)

        # 创建方向显示区域
        self.GUI_ori_layout = QHBoxLayout()
        self.GUI_ori_data_layout = QHBoxLayout()
        self.GUI_ori_label = QLabel("Orientation:")
        self.GUI_ori_data = LineEdit(type='output')
        self.GUI_set_ori_data = LineEdit(type='input')
        self.GUI_set_ori_data.setObjectName('GUI_ori_data')
        self.GUI_ori_data.setReadOnly(True)
        self.GUI_ori_data.setFocusPolicy(Qt.NoFocus)
        self.GUI_copy_ori_btn = QPushButton("Copy")
        self.GUI_copy_ori_btn.line_edit = self.GUI_ori_data
        self.GUI_set_ori_btn = QPushButton("Set")
        self.GUI_set_ori_btn.line_edit = self.GUI_set_ori_data
        self.GUI_ori_layout.addWidget(self.GUI_ori_label)
        self.GUI_ori_layout.addWidget(self.GUI_copy_ori_btn)
        self.GUI_ori_layout.addWidget(self.GUI_set_ori_btn)
        self.GUI_ori_data_layout.addWidget(self.GUI_ori_data)
        self.GUI_ori_data_layout.addWidget(self.GUI_set_ori_data)

        # 创建关节角度显示区域
        self.GUI_joints_angle_layout = QHBoxLayout()
        self.GUI_joints_angle_data_layout = QHBoxLayout()
        self.GUI_joints_angle_label = QLabel("Joints Angles:")
        self.GUI_joints_angle_data = LineEdit(type='output')
        self.GUI_set_joints_angle_data = LineEdit(type='input')
        self.GUI_set_joints_angle_data.setObjectName('GUI_joints_angle_data')
        self.GUI_joints_angle_data.setReadOnly(True)
        self.GUI_joints_angle_data.setFocusPolicy(Qt.NoFocus)
        self.GUI_copy_joints_angle_btn = QPushButton("Copy")
        self.GUI_copy_joints_angle_btn.line_edit = self.GUI_joints_angle_data
        self.GUI_set_joints_angle_btn = QPushButton("Set")
        self.GUI_set_joints_angle_btn.line_edit = self.GUI_set_joints_angle_data
        self.GUI_joints_angle_layout.addWidget(self.GUI_joints_angle_label)
        self.GUI_joints_angle_layout.addWidget(self.GUI_copy_joints_angle_btn)
        self.GUI_joints_angle_layout.addWidget(self.GUI_set_joints_angle_btn)
        self.GUI_joints_angle_data_layout.addWidget(self.GUI_joints_angle_data)
        self.GUI_joints_angle_data_layout.addWidget(self.GUI_set_joints_angle_data)

        # 添加组件到布局
        self.GUI_data_layout.addLayout(self.GUI_pos_layout)
        self.GUI_data_layout.addLayout(self.GUI_pos_data_layout)
        self.GUI_data_layout.addLayout(self.GUI_ori_layout)
        self.GUI_data_layout.addLayout(self.GUI_ori_data_layout)
        self.GUI_data_layout.addLayout(self.GUI_joints_angle_layout)
        self.GUI_data_layout.addLayout(self.GUI_joints_angle_data_layout)

    def get_tcp_coordinates(self):
        """获取机械臂TCP坐标的按钮事件"""
        tcp_coordinates = {"x": 1.23, "y": 4.56, "z": 7.89}
        quaternion = {"qx": 0.12, "qy": 0.34, "qz": 0.56, "qw": 0.78}
        self.update_coord_display(tcp_coordinates, quaternion)


    def update_coord_display(self, coordinates, quaternion):
        """更新坐标和四元数的显示"""
        xyz_text = f"X = {coordinates['x']:.2f}, Y = {coordinates['y']:.2f}, Z = {coordinates['z']:.2f}"
        quaternion_text = f"qx = {quaternion['qx']:.2f}, qy = {quaternion['qy']:.2f}, qz = {quaternion['qz']:.2f}, qw = {quaternion['qw']:.2f}"

        # 更新LineEdit中的文本
        self.GUI_pos_data.setText(xyz_text)
        self.GUI_ori_data.setText(quaternion_text)
        self.GUI_joints_angle_data.setText("Joint angles display here")

    def update_joint_angles_display(self, joint_angles):
        """更新关节角度的显示"""
        joint_angles_text = ", ".join([f"{angle:.5f}" for angle in joint_angles])
        self.GUI_joints_angle_data.setText(joint_angles_text)


    def on_show_tcp_axis_btn_clicked(self):
        """显示TCP坐标系轴的按钮事件"""

        if self.show_tcp_axis_btn.text() == "显示TCP坐标轴":
            self.show_tcp_axis_btn.setText("隐藏TCP坐标轴")
            self.show_tcp_axis_changed.emit(True)
        else:
            self.show_tcp_axis_btn.setText("显示TCP坐标轴")
            self.show_tcp_axis_changed.emit(False)

    def on_show_axis_changed(self, ifshow:bool):
        """处理显示TCP坐标轴状态变化的槽函数"""
        asyncio.run_coroutine_threadsafe(self.simulation_view.pybullet_process.env.show_tcp_axis(ifshow), self.simulation_view.env_loop)

    def on_get_tcp_btn_clicked(self):
        """获取机械臂TCP坐标的按钮事件"""
        asyncio.run_coroutine_threadsafe(self.get_tcp_pos_and_ori(),
                                         self.simulation_view.env_loop)

        pass

    async def get_tcp_pos_and_ori(self):
        data = await self.simulation_view.pybullet_process.env.get_tcp_pos_and_ori()
        status = data.get("status",None)
        try:
            if status is not None and status=="success":
                pos, ori = data["message"]["pos"], data["message"]["ori"]
                coordinates = {"x":pos[0],"y":pos[1],"z":pos[2]}
                quaternion = {"qx":ori[0],"qy":ori[1],"qz":ori[2],"qw":ori[3]}
                self.tcp_pos_and_ori.emit(coordinates, quaternion)
            else:
                print("[ArmToolPage:get_tcp_pos_and_ori]获取TCP坐标失败:", data.get("message","Unknown error"))
        except Exception as e:
            print("[ArmToolPage:get_tcp_pos_and_ori]获取TCP坐标异常:", str(e))

    def on_get_robot_end_effector_btn_clicked(self):
        """获取机械臂末端坐标的按钮事件"""
        asyncio.run_coroutine_threadsafe(self.get_robot_end_effector_pos_and_ori(),
                                         self.simulation_view.env_loop)
        pass

    async def get_robot_end_effector_pos_and_ori(self):
        data = await self.simulation_view.pybullet_process.env.get_robot_end_effector_pos_and_ori()
        status = data.get("status", None)
        try:
            if status is not None and status == "success":
                pos, ori = data["message"]["pos"], data["message"]["ori"]
                coordinates = {"x": pos[0], "y": pos[1], "z": pos[2]}
                quaternion = {"qx": ori[0], "qy": ori[1], "qz": ori[2], "qw": ori[3]}
                self.end_effector_pos_and_ori.emit(coordinates, quaternion)
            else:
                print("[ArmToolPage:get_tcp_pos_and_ori]获取TCP坐标失败:", data.get("message", "Unknown error"))
        except Exception as e:
            print("[ArmToolPage:get_tcp_pos_and_ori]获取TCP坐标异常:", str(e))
        pass


    def on_subscribe_btn_clicked(self):
        if self.subscribe_btn.text() == "订阅机械臂状态":
            self.subscribe_btn.setText("取消订阅机械臂状态")
            self.subscribe_btn.setStyleSheet("background-color: lightgreen;")
            self.subscribe_changed.emit(True)
        else:
            self.subscribe_btn.setText("订阅机械臂状态")
            self.subscribe_btn.setStyleSheet("")
            self.subscribe_changed.emit(False)

    def on_subscribe_changed(self,on_subscribe):
        asyncio.run_coroutine_threadsafe(self.simulation_view.pybullet_process.env.subscribe_robot_state(on_subscribe),
                                         self.simulation_view.env_loop)

    def copy_data(self):
        self.current_button = self.sender()  # 获取触发信号的按钮

        try:
            """复制位置数据到剪贴板"""
            data = self.current_button.line_edit.text()  # 通过按钮访问 QLineEdit
            QApplication.clipboard().setText(data)
            # # 显示对钩图标来表示复制成功
            # icon_size = self.GUI_copy_pos_btn.sizeHint()
            # self.GUI_copy_pos_btn.setIcon(QIcon(QPixmap('resources/images/green.png').scaled(icon_size, transformMode=Qt.SmoothTransformation)))
            # self.GUI_copy_pos_btn.setLayoutDirection(Qt.RightToLeft)
            # self.GUI_copy_pos_btn.setIconSize(icon_size)
            self.current_button.setText('Copy √!')
            # 设置定时器清除图标
            QTimer.singleShot(500, self.clear_icon)  # 2秒后清除图标
            # QMessageBox.information(self, "Copied", "Position data copied to clipboard!")
        except Exception as e:
            print(f"Error copy pos data: {str(e)}")

    def clear_icon(self):
        try:
            # 清除按钮的图标
            # self.GUI_copy_pos_btn.setIcon(QIcon())
            self.current_button.setText('Copy')
        except Exception as e:
            print(f"Error clear icon: {str(e)}")

    @staticmethod
    def extract_floats_from_text(data_str: str):
        # 使用正则表达式提取所有浮点数
        pattern = r"[-+]?\d*\.\d+|\d+"  # 匹配浮动点数
        float_values = re.findall(pattern, data_str)

        # 将字符串列表转换为浮动点数列表
        return [float(value) for value in float_values]

    def on_set_robot_data(self):
        button = self.sender()  # 获取触发信号的按钮
        button_name = button.objectName()  # 获取按钮对象的

        try:
            pos_data = self.GUI_set_pos_btn.line_edit.text()
            ori_data = self.GUI_set_ori_btn.line_edit.text()
            pos_data = self.extract_floats_from_text(pos_data)
            ori_data = self.extract_floats_from_text(ori_data)
            if pos_data and ori_data:
                asyncio.run_coroutine_threadsafe(
                    self.simulation_view.pybullet_process.env.set_robot_end_pos_and_ori(pos_data, ori_data, maxVelocity=0.5),
                    self.simulation_view.env_loop)
        except Exception as e:
            print(f"[ArmToolPage:on_set_robot_data] Error set robot data: {str(e)}")

    def on_set_robot_joint_data(self):
        try:
            joints_data = self.GUI_set_joints_angle_btn.line_edit.text()
            joints_data = self.extract_floats_from_text(joints_data)
            if joints_data:
                asyncio.run_coroutine_threadsafe(
                    self.simulation_view.pybullet_process.env.set_robot_joints(joints_data, maxVelocity=0.5),
                    self.simulation_view.env_loop)
        except Exception as e:
            print(f"[ArmToolPage:on_set_robot_joint_data] Error set robot data: {str(e)}")

    def on_synchronize_DT_btn_clicked(self):
        """同步数字孪生状态按钮事件"""
        try:

            coro = self.simulation_view.pybullet_process.env.get_DT_robot_joints_state()
            self.async_runner_for_synchronize_digital_twin_state.run(self.simulation_view.env_loop, coro)

        except Exception as e:
            print(f"[ArmToolPage:on_synchronize_DT_btn_clicked] Error synchronize DT state: {str(e)}")
        pass

    def handle_synchronize_DT_result(self, result):
        """处理同步数字孪生状态的结果"""
        status = result.get("status", None)
        joints = result.get("joints_state", None)
        if status is not None and status == "success" and joints is not None:
            asyncio.run_coroutine_threadsafe(
                self.simulation_view.pybullet_process.env.reset_joints_state(joints),
                self.simulation_view.env_loop)
            print("[ArmToolPage:handle_synchronize_DT_result] 同步数字孪生状态成功")
        else:
            print("[ArmToolPage:handle_synchronize_DT_result] 同步数字孪生状态失败:", result.get("message", "Unknown error"))



class MachineToolPage(QWidget):
    """机床工具页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel("机床工具页面")
        layout.addWidget(self.label)

        # 在此页面中添加具体的机床工具组件



class PathToolPage(QWidget):
    """路径规划工具页面"""
    plan_finished = pyqtSignal(dict)
    execute_finished = pyqtSignal(dict)
    def __init__(self, parent=None,tool_pannel=None):
        super().__init__(parent)
        self.tool_pannel = tool_pannel
        self.layout = QVBoxLayout(self)
        self.label = QLabel("路径规划工具页面")
        self.layout.addWidget(self.label)

        self.paths_dict = {}
        self.num_path = 1
        self.init_ui()


    def init_ui(self):
        # ===================== 1. 规划算法选择（顶部） =====================
        algo_layout = QHBoxLayout()
        algo_label = QLabel("Planner:", self)
        self.planner_combo = QComboBox(self)
        # 这里先放几个占位的规划算法名称，你可以按实际再改
        self.planner_combo.addItems([
            "RRTConnect_Custom",
            "RRTConnect",
            "PRM",
            "TaskSpaceRRT"
        ])

        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(self.planner_combo)
        algo_layout.addStretch(1)

        self.layout.addLayout(algo_layout)

        # ===================== 2. Start / Target joints 行 =====================
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)

        # ---- Start joints 行 ----
        start_row = QHBoxLayout()
        self.start_joints_edit = QLineEdit(self)
        self.start_joints_edit.setPlaceholderText("j1, j2, j3, j4, j5, j6 （弧度）")
        btn_start_copy = QPushButton("Copy From Sim", self)
        btn_start_copy.clicked.connect(self.on_copy_start_from_sim_clicked)

        start_row.addWidget(self.start_joints_edit)
        start_row.addWidget(btn_start_copy)

        form_layout.addRow("Start joints:", start_row)

        # ---- Target joints 行 ----
        target_row = QHBoxLayout()
        self.target_joints_edit = QLineEdit(self)
        self.target_joints_edit.setPlaceholderText("j1, j2, j3, j4, j5, j6 （弧度）")
        btn_target_copy = QPushButton("Copy From Sim", self)
        btn_target_copy.clicked.connect(self.on_copy_target_from_sim_clicked)

        target_row.addWidget(self.target_joints_edit)
        target_row.addWidget(btn_target_copy)

        form_layout.addRow("Target joints:", target_row)

        self.layout.addLayout(form_layout)

        # ===================== 3. 下方操作按钮行 =====================
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)


        self.btn_plan = QPushButton("Plan", self)
        self.btn_execute = QPushButton("Execute", self)
        self.btn_inverse = QPushButton("Inverse", self)

        self.btn_plan.clicked.connect(self.on_plan_clicked)
        self.plan_finished.connect(self.on_plan_finished_in_gui)
        self.btn_execute.clicked.connect(self.on_execute_clicked)
        self.execute_finished.connect(self.on_execute_finished_in_gui)
        self.btn_inverse.clicked.connect(self.on_inverse_clicked)

        btn_row.addWidget(self.btn_plan)
        btn_row.addWidget(self.btn_execute)
        btn_row.addWidget(self.btn_inverse)

        self.layout.addLayout(btn_row)

        self._build_path_table(self.layout)

        # 填充一下底部空间，让内容靠上
        self.layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _build_path_table(self, parent_layout: QVBoxLayout):
        """构建路径列表表格，用于显示所有规划出的路径"""
        self.paths_table = QTableWidget(self)
        self.paths_table.setColumnCount(3)
        self.paths_table.setHorizontalHeaderLabels(["Name", "Points", "Remark"])
        self.paths_table.verticalHeader().setVisible(False)
        self.paths_table.setSelectionBehavior(self.paths_table.SelectRows)
        self.paths_table.setSelectionMode(self.paths_table.SingleSelection)
        self.paths_table.setEditTriggers(self.paths_table.NoEditTriggers)
        self.paths_table.setAlternatingRowColors(True)

        header = self.paths_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name 列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # 单击：选中对应路径
        self.paths_table.itemClicked.connect(self.on_path_item_clicked)
        # 双击：打开 PathDataDialog 查看数据
        self.paths_table.itemDoubleClicked.connect(self.on_path_item_double_clicked)
        # 启用自定义右键菜单
        self.paths_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.paths_table.customContextMenuRequested.connect(self.on_paths_table_context_menu)

        parent_layout.addWidget(self.paths_table)

    def on_copy_start_from_sim_clicked(self):
        """
        然后填入 self.start_joints_edit，例如格式：'0.0, 1.0, 0.5, ...'
        """
        try:
            if not hasattr(self.tool_pannel, "arm_tool_page") or self.tool_pannel.arm_tool_page is None:
                print("[PathToolPage] ToolPage not set.")
                return
            if not hasattr(self.tool_pannel.arm_tool_page,
                           "GUI_joints_angle_data") or self.tool_pannel.arm_tool_page.GUI_joints_angle_data is None:
                print("[PathToolPage] 请打开仿真环境的机械臂状态订阅器.")
                return

            joints_text = self.tool_pannel.arm_tool_page.GUI_joints_angle_data.text()
            angles_str_list = [s.strip() for s in joints_text.split(',')]
            if not all(angles_str_list):
                print("[PathToolPage] 仿真环境的机械臂状态数据不正确，请打开.")
                logging.info("[PathToolPage] 仿真环境的机械臂状态数据不正确，请打开.")
                return
            joint_angles = list(map(float, angles_str_list))
            start_text = ", ".join(f"{j:.5f}" for j in joint_angles)
            self.start_joints_edit.setText(start_text)
            print("[PathToolPage] Copied joint state from simulation.")
            logging.info("[PathToolPage] Copied joint state from simulation.")
        except Exception as e:
            print(f"[PathToolPage:on_copy_start_from_sim_clicked] Error: {e}")
            logging.info(f"[PathToolPage:on_copy_start_from_sim_clicked] Error: {e}")

    def on_copy_target_from_sim_clicked(self):
        """
        """
        try:
            if not hasattr(self.tool_pannel, "arm_tool_page") or self.tool_pannel.arm_tool_page is None:
                print("[PathToolPage] ToolPage not set.")
                return
            if not hasattr(self.tool_pannel.arm_tool_page,"GUI_joints_angle_data") or self.tool_pannel.arm_tool_page.GUI_joints_angle_data is None:
                print("[PathToolPage] 请打开仿真环境的机械臂状态订阅器.")
                return

            joints_text = self.tool_pannel.arm_tool_page.GUI_joints_angle_data.text()
            angles_str_list = [s.strip() for s in joints_text.split(',')]
            if not all(angles_str_list):
                logging.info("[PathToolPage] 仿真环境的机械臂状态数据不正确，请打开.")
                return
            joint_angles = list(map(float, angles_str_list))
            target_text = ", ".join(f"{j:.5f}" for j in joint_angles)
            self.target_joints_edit.setText(target_text)
            logging.info("[PathToolPage] Copied joint state from simulation.")
        except Exception as e:
            logging.info(f"[PathToolPage:on_copy_target_from_sim_clicked] Error: {e}")


    def on_plan_clicked(self):
        """
        将规划出的 path 保存到某个结构里，或显示在别的控件中。
        """
        try:
            planner_name = self.planner_combo.currentText()
            logging.info(f"[PathToolPage] Plan clicked. planner={planner_name}")
            start_text = self.start_joints_edit.text().strip()  # 逗号分隔的字符串
            target_text = self.target_joints_edit.text().strip()

            start_angles_str_list = [s.strip() for s in start_text.split(',')]
            if not all(start_angles_str_list):
                logging.info("[PathToolPage] start joints 数据不正确.")
                return
            start_joint_angles = list(map(float, start_angles_str_list))
            logging.info(f"  start joints: {start_text}")
            target_angles_str_list = [s.strip() for s in target_text.split(',')]
            if not all(target_angles_str_list):
                logging.info("[PathToolPage] target joints 数据不正确.")
                return
            target_joint_angles = list(map(float, target_angles_str_list))
            logging.info(f"  target joints: {target_text}")

            request = PathPlanRequest(
                planner_name=planner_name,
                start_joints = start_joint_angles,
                target_joints = target_joint_angles
            )
            future = asyncio.run_coroutine_threadsafe(self.tool_pannel.simulation_view.pybullet_process.env.plan_path(request),
                                                      self.tool_pannel.simulation_view.env_loop)
            # 修改plan按钮的颜色为黄色，表示正在规划中
            self.btn_plan.setStyleSheet("background-color: yellow")
            self.btn_plan.setText("Planning...")
            self.btn_plan.setEnabled(False)

            # 注册连接完成后的回调函数（关键：通过回调处理结果）
            future.add_done_callback(lambda f: self.on_plan_done(f))
        except Exception as e:
            self.plan_finished.emit({"status":"error","message":str(e)})
            print(f"[PathToolPage:on_plan_clicked] Error: {e}")

    def on_plan_finished_in_gui(self, result: dict):
        if result.get("status") == "success":
            logging.info("[PathToolPage] Path planning succeeded.")
            self.btn_plan.setStyleSheet("background-color: green")
            self.btn_plan.setText("Plan")
            self.btn_plan.setEnabled(True)
            # 2. 使用 QTimer.singleShot 在 2 秒后执行恢复操作
            # lambda 表达式用于传递额外的参数（原始样式和文本）
            QTimer.singleShot(
                2000,
                lambda: self.btn_plan.setStyleSheet("")
            )
            ...
        else:
            error = result.get("message","")
            logging.info(f"[PathToolPage] Path planning failed. error:{error}")
            self.btn_plan.setStyleSheet("background-color: red")
            self.btn_plan.setText("Plan")
            self.btn_plan.setEnabled(True)
            QTimer.singleShot(
                2000,
                lambda: self.btn_plan.setStyleSheet("")
            )
            ...

    def on_plan_done(self, future):
        """路径规划完成后的回调函数（处理结果并更新UI）"""
        try:
            # 获取异步连接的返回结果
            result = future.result()
            # 根据连接结果判断（假设成功时result无error字段）
            if result.get("status") == "success":
                self.plan_finished.emit(result)  # Qt 自动把信号投递到 GUI 线程
                path = result.get("path", [])
                name = f"path_{self.num_path:04d}"
                self.paths_dict[name] = path

                self.num_path+=1

                # 更新表格
                self.add_path_to_table(name, path)
            else:
                # 连接失败（如API返回错误）
                logging.info("[PathToolPage] Path planning failed.")
                self.plan_finished.emit(result)
                pass
        except Exception as e:
            self.plan_finished.emit(result)
            # 连接过程中发生异常（如超时、网络错误）
            print(f"Connection failed: {e}")




    def add_path_to_table(self, name: str, path):
        """在表格中增加一条路径记录"""
        row = self.paths_table.rowCount()
        self.paths_table.insertRow(row)

        # Name 列
        item_name = QTableWidgetItem(name)
        item_name.setTextAlignment(Qt.AlignCenter)
        self.paths_table.setItem(row, 0, item_name)

        # Points 列：路径包含的点数
        n_points = len(path) if path is not None else 0
        item_points = QTableWidgetItem(str(n_points))
        item_points.setTextAlignment(Qt.AlignCenter)
        self.paths_table.setItem(row, 1, item_points)

        # Remark 列：先简单空着，后面你可以写 planner 名称、时间等
        remark = ""
        item_remark = QTableWidgetItem(remark)
        item_remark.setTextAlignment(Qt.AlignCenter)
        self.paths_table.setItem(row, 2, item_remark)


    def on_path_item_clicked(self, item):
        """单击路径行：选中对应路径"""
        row = item.row()
        name_item = self.paths_table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()
        self.current_path_name = name
        # 你可以在这里做一些 UI 提示，比如在状态栏打印
        print(f"[PathToolPage] selected path: {name}")

    def on_path_item_double_clicked(self, item):
        """双击路径行：用 PathDataDialog 查看该路径的关节数据"""
        row = item.row()
        name_item = self.paths_table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()

        path_data = self.paths_dict.get(name)
        if path_data is None:
            print(f"[PathToolPage] no path data for: {name}")
            return

        dlg = PathDataDialog(path_data, name,sim_view=self.tool_pannel.simulation_view)
        dlg.show()  # 非阻塞
        dlg.raise_()
        dlg.activateWindow()

        # 为防止被 GC 回收，保留引用
        self._last_data_dialog = dlg


    def on_paths_table_context_menu(self, pos: QPoint):
        """路径表右键菜单：Remove / Save to XML"""
        index = self.paths_table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        name_item = self.paths_table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()

        menu = QMenu(self)

        act_remove = QAction("Remove", self)
        act_export = QAction("Save to XML...", self)

        menu.addAction(act_remove)
        menu.addAction(act_export)

        action = menu.exec_(self.paths_table.viewport().mapToGlobal(pos))
        if action is None:
            return

        if action == act_remove:
            self._remove_path(name, row)
        elif action == act_export:
            self._export_path_to_xml(name)

    def _remove_path(self, name: str, row: int):
        """从表格 & 字典中删除路径"""
        # 删表格行
        self.paths_table.removeRow(row)
        # 删数据
        if name in self.paths_dict:
            del self.paths_dict[name]
        # 如果当前选中正好是它，清空 current_path_name
        if self.current_path_name == name:
            self.current_path_name = None
        print(f"[PathToolPage] removed path: {name}")

    def _export_path_to_xml(self, name: str):
        """将指定路径保存为 XML 文件"""
        path = self.paths_dict.get(name)
        if not path:
            print(f"[PathToolPage] no path data to export for: {name}")
            return

        # 你可以改成自己的默认目录
        default_dir = "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/assets/datas/test_datas"
        default_name = f"{name}.xml"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Path as XML",
            os.path.join(default_dir, default_name),
            "XML files (*.xml)"
        )
        if not filename:
            return

        # 按你之前的格式写 XML：
        # <RobotPath>
        #   <Point id="1">
        #       <Joint1>...</Joint1> ...
        #   </Point>
        root = ET.Element("RobotPath")
        for idx, joints in enumerate(path, start=1):
            point_elem = ET.SubElement(root, "Point", id=str(idx))
            for j_idx, val in enumerate(joints, start=1):
                joint_elem = ET.SubElement(point_elem, f"Joint{j_idx}")
                joint_elem.text = str(val)

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"[PathToolPage] path '{name}' exported to: {filename}")



    def on_execute_clicked(self):
        """
        TODO: 执行已规划好的路径：可以发给仿真环境，也可以发给物理层 driver。
        """
        try:
            if not hasattr(self, "current_path_name"):
                logging.info("[PathToolPage] 请先选择一个规划好的路径.")
                return
            path_name = self.current_path_name
            path = self.paths_dict.get(path_name)
            if path is None:
                logging.info(f"[PathToolPage] 未找到路径数据: {path_name}")
                return

            request = ExecutePathRequest(
                joints_list=path,
            )
            future = asyncio.run_coroutine_threadsafe(
                self.tool_pannel.simulation_view.pybullet_process.env.execute_path(request),
                self.tool_pannel.simulation_view.env_loop)
            # 修改plan按钮的颜色为黄色，表示正在规划中
            self.btn_execute.setStyleSheet("background-color: yellow")
            self.btn_execute.setText("Executing...")
            self.btn_execute.setEnabled(False)

            # 注册连接完成后的回调函数（关键：通过回调处理结果）
            future.add_done_callback(lambda f: self.on_execute_done(f))
        except Exception as e:
            print(f"[PathToolPage:on_plan_clicked] Error: {e}")

    def on_execute_done(self,future):
        """路径执行完成后的回调函数（处理结果并更新UI）"""
        try:
            # 获取异步连接的返回结果
            result = future.result()
            # 根据连接结果判断（假设成功时result无error字段）
            if result.get("status") == "success":
                logging.info("[PathToolPage] Path execution succeeded.")
                self.execute_finished.emit(result)  # Qt 自动把信号投递到 GUI 线程
                ...
            else:
                logging.info("[PathToolPage] Path execution failed.")
                self.execute_finished.emit(result)
                ...
        except Exception as e:
            # 连接过程中发生异常（如超时、网络错误）
            print(f"Connection failed: {e}")

    def on_execute_finished_in_gui(self,result: dict):
        if result.get("status") == "success":
            self.btn_execute.setStyleSheet("background-color: green")
            self.btn_execute.setText("execute")
            self.btn_execute.setEnabled(True)
            # 2. 使用 QTimer.singleShot 在 2 秒后执行恢复操作
            # lambda 表达式用于传递额外的参数（原始样式和文本）
            QTimer.singleShot(
                2000,
                lambda: self.btn_execute.setStyleSheet("")
            )
            ...
        else:
            ...

    def on_inverse_clicked(self):
        """
        TODO: 对现在已有 path 做反向（例如 path[::-1]），
        或者 start/target 交换后再规划，按你的需求定义。
        """
        print("[PathToolPage] Inverse clicked (待实现)")



class OtherToolPage(QWidget):
    """其他工具页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel("其他工具页面")
        layout.addWidget(self.label)

        # 在此页面中添加其他工具组件





class ToolPanel(QWidget):
    """仿真工具面板，用于展示不同的工具页面（机械臂工具、机床工具、其他工具）"""

    def __init__(self, parent=None,simulation_view=None):
        super().__init__(parent)
        self.simulation_view = simulation_view

        # 布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 1. 工具选择下拉框
        # 1. 顶部工具按钮条（代替 QComboBox）
        # === 新增：一个有边框的整体容器 frame ===
        self.panel_frame = QFrame(self)
        self.panel_frame.setObjectName("toolPanelFrame")
        panel_layout = QVBoxLayout(self.panel_frame)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        self._build_toolbar(panel_layout)
        self.layout.addWidget(self.panel_frame)

        # self.page_selector = QComboBox()
        # self.page_selector.addItem("机械臂工具")
        # self.page_selector.addItem("机床工具")
        # self.page_selector.addItem("路径规划工具")
        # self.page_selector.addItem("其他工具")
        # self.page_selector.currentIndexChanged.connect(self.switch_page)
        # self.layout.addWidget(self.page_selector)

        # 2. QStackedWidget 用于管理工具页面
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setContentsMargins(4, 4, 4, 4)  # 去除 QStackedWidget 的内边距

        # 创建每个工具页面
        self.arm_tool_page = ArmToolPage(simulation_view=self.simulation_view)
        self.machine_tool_page = MachineToolPage()
        self.path_tool_page = PathToolPage(tool_pannel=self)
        self.other_tool_page = OtherToolPage()

        # 将页面添加到 QStackedWidget
        self.stacked_widget.addWidget(self.arm_tool_page)
        self.stacked_widget.addWidget(self.machine_tool_page)
        self.stacked_widget.addWidget(self.path_tool_page)
        self.stacked_widget.addWidget(self.other_tool_page)

        # 将 QStackedWidget 添加到布局
        panel_layout.addWidget(self.stacked_widget)

        # 设置默认页面
        self.stacked_widget.setCurrentIndex(0)  # 默认显示机械臂工具页面

        # 去除每个页面的布局间隙
        self.remove_layout_spacing(self.arm_tool_page)
        self.remove_layout_spacing(self.machine_tool_page)
        self.remove_layout_spacing(self.path_tool_page)
        self.remove_layout_spacing(self.other_tool_page)

    def _build_toolbar(self, parent_layout):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)  # 互斥选择

        # 定义按钮配置： (index, text, icon_path)
        # icon_path 你可以自己换成实际的图标路径，或者先 None
        btn_configs = [
            (0, "机械臂", "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/ui/resources/icons/robot.png"),
            (1, "机床", "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/ui/resources/icons/machine.png"),
            (2, "路径规划", "/home/lwh/Project/python_project/Ai_agent/agent_project_v2/ui/resources/icons/path.png"),
            (3, "其他", None),
        ]

        BTN_SIZE = 25  # 按钮宽高（图标最大化填充）
        ICON_MARGIN = 10  # 图标四周预留的边距（减少压迫感）

        self.toolbar_buttons = []

        for index, text, icon_path in btn_configs:
            btn = QToolButton(self)
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setFixedSize(BTN_SIZE, BTN_SIZE)
            # btn.setAutoRaise(False)

            if icon_path:
                # pix = QPixmap(icon_path).scaled(
                #     20,20,
                #     Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                # )
                # btn.setIcon(QIcon(pix))
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(BTN_SIZE-ICON_MARGIN, BTN_SIZE-ICON_MARGIN))

            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))

            toolbar_layout.addWidget(btn)
            self.btn_group.addButton(btn, index)
            self.toolbar_buttons.append(btn)

        toolbar_layout.addStretch(1)  # 右侧留一点空白

        # 简单的样式，美化一下按钮
        self.setStyleSheet("""
                QToolButton {
                    border: none;
                    margin: 0px;
                    border-radius: 0px;
                    padding: 0px;
                    background-color: #ffffff;
                    color: #dddddd;
                }
                QToolButton:checked {
                    background-color: #007acc;
                    border-color: #0088ff;
                    color: white;
                }
                QToolButton:hover {
                    background-color: #505357;
                }
                """)

        parent_layout.addLayout(toolbar_layout)
        self._apply_style()
        pass

    def _apply_style(self):
        self.setStyleSheet("""
        /* 整个工具面板的外框 */
        QFrame#toolPanelFrame {
            border: 1px solid #555555;
            border-radius: 0px;
            background-color: #eeeeee;
        }

        /* 顶部按钮：未选中状态 */
        QToolButton {
            border: 1px solid #555555;
            border-bottom: none;                /* 底边让给内容区域 */
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
            padding: 0px 0px;
            background-color: #aaaaaa;
            color: #dddddd;
        }

        /* 鼠标悬停 */
        QToolButton:hover {
            background-color: #4b4f52;
        }

        /* 选中的按钮：像激活的 Tab */
        QToolButton:checked {
            background-color: #ffffff;
            border-color: #409eff;
            color: white;
        }

        /* 内容区域：与按钮共享同一边框 */
        QStackedWidget {
            border-top: 1px solid #ffffff;      /* 补上被按钮“挖走”的那条缝 */
            border-left: none;
            border-right: none;
            border-bottom: none;
            background-color: #ffffff;
        }
        """)

    def switch_page(self, index):
        """切换工具页面"""
        self.stacked_widget.setCurrentIndex(index)

    def remove_layout_spacing(self, page_widget):
        """移除页面中的间隙"""
        for layout in page_widget.findChildren(QLayout):
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)


# ==============================================================
# 调试入口
# ==============================================================
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    # 创建一个QApplication实例
    app = QApplication(sys.argv)

    # 创建并显示仿真视图
    window = ToolPanel()
    window.show()

    # 启动应用程序
    sys.exit(app.exec_())
