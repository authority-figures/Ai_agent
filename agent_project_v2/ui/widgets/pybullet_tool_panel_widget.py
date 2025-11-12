import json

from PyQt5.QtCore import pyqtSignal, Qt, QEvent, QThread


from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QStackedWidget, QComboBox, QLabel,
                             QLineEdit, QSizePolicy, QGroupBox, QLayout
                             )
import asyncio
import websockets

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
        async with websockets.connect(uri) as websocket:
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
        joint_angles_text = ", ".join([f"{angle:.2f}" for angle in joint_angles])
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
            self.subscribe_changed.emit(True)
        else:
            self.subscribe_btn.setText("订阅机械臂状态")
            self.subscribe_changed.emit(False)

    def on_subscribe_changed(self,on_subscribe):
        asyncio.run_coroutine_threadsafe(self.simulation_view.pybullet_process.env.subscribe_robot_state(on_subscribe),
                                         self.simulation_view.env_loop)


class MachineToolPage(QWidget):
    """机床工具页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel("机床工具页面")
        layout.addWidget(self.label)

        # 在此页面中添加具体的机床工具组件

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
        self.page_selector = QComboBox()
        self.page_selector.addItem("机械臂工具")
        self.page_selector.addItem("机床工具")
        self.page_selector.addItem("其他工具")
        self.page_selector.currentIndexChanged.connect(self.switch_page)
        self.layout.addWidget(self.page_selector)

        # 2. QStackedWidget 用于管理工具页面
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setContentsMargins(0, 0, 0, 0)  # 去除 QStackedWidget 的内边距

        # 创建每个工具页面
        self.arm_tool_page = ArmToolPage(simulation_view=self.simulation_view)
        self.machine_tool_page = MachineToolPage()
        self.other_tool_page = OtherToolPage()

        # 将页面添加到 QStackedWidget
        self.stacked_widget.addWidget(self.arm_tool_page)
        self.stacked_widget.addWidget(self.machine_tool_page)
        self.stacked_widget.addWidget(self.other_tool_page)

        # 将 QStackedWidget 添加到布局
        self.layout.addWidget(self.stacked_widget)

        # 设置默认页面
        self.stacked_widget.setCurrentIndex(0)  # 默认显示机械臂工具页面

        # 去除每个页面的布局间隙
        self.remove_layout_spacing(self.arm_tool_page)
        self.remove_layout_spacing(self.machine_tool_page)
        self.remove_layout_spacing(self.other_tool_page)

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
