import asyncio
import sys
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QWindow, QFont
import Xlib
import Xlib.display
from Xlib import X
from PyQt5.QtCore import QTimer, Qt, QProcess, QThread, QRect
import subprocess
from execution.simulation.simulation_process import PyBulletProcess
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal
from ui.widgets.pybullet_tool_panel_widget import ToolPanel




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
                return int(window_ids[0])

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



class SimulationView(QWidget):
    """仿真视图，用于嵌入PyBullet窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 启动PyBullet仿真
        self.pybullet_process = PyBulletProcess()
        self.pybullet_process.start()
        self.env_loop = self.pybullet_process.loop
        # layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        #
        # # 状态标签
        # self.label = QLabel("Initializing PyBullet simulation...")
        # self.label.setAlignment(Qt.AlignCenter)
        # self.label.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Minimum)
        # layout.addWidget(self.label)
        #
        # self.control_panel = ControlPanel()
        # layout.addWidget(self.control_panel)
        #
        # # 容器用于嵌入窗口
        # self.container = QWidget(self)
        # # self.container.setMinimumSize(800, 500)
        # # 让pybullet窗口尽量铺满
        # self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 给当前视图设置ID，确保样式表只作用于SimulationView自身
        self.setObjectName("SimulationView")
        self.setStyleSheet("""
            SimulationView#SimulationView {
                /* ---- 背景：冷亮灰，带轻微透明度 ---- */
                background-color: rgba(240, 242, 245, 0.95);

                /* ---- 边框：2 px 圆角 + 内发光 ---- */
                border: 5px solid rgba(100, 150, 255, 0.5);
                border-radius: 0px;

                /* ---- 内发光（Qt 支持 box-shadow） ---- */
                /*box-shadow: inset 0 0 8px rgba(100, 150, 255, 0.25);*/

                /* ---- 顶部彩色条：4 px 渐变蓝 ---- */
                border-top: 4px solid qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4facfe,
                    stop:1 #00f2fe
                );

                /* ---- 内边距：让控件不贴边 ---- */
                padding: 20px;
            }
        """)

        # ===== 关键修复 =====
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.ensurePolished()
        self.setAutoFillBackground(True)

        # ==============================================
        # 2. 主布局：管理内部所有控件（标题+状态+控制+仿真容器）
        # ==============================================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)  # 布局与视图边界贴合（依赖视图的padding）
        main_layout.setSpacing(12)  # 控件之间的间距，提升分层感

        # ==============================================
        # 3. 新增：模块标题栏（强化“仿真区域”的独立性）
        # ==============================================
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 标题文本：加粗+放大，明确模块用途
        self.title_label = QLabel("仿真区域")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setStyleSheet("color: #212529;")

        # 标题栏右侧留白（通过拉伸因子让标题靠左）
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)

        main_layout.addLayout(title_layout)

        # ==============================================
        # 4. 状态标签：保持功能，优化视觉（与标题栏呼应）
        # ==============================================
        self.label = QLabel("Initializing PyBullet simulation...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #343a40;
                        background-color: #e9ecef;
                        border-radius: 6px;
                        padding: 8px 12px;
                    }
                """)
        # main_layout.addWidget(self.label) # 没必要显示该状态栏

        # ==============================================
        # 5. 控制面板：保持功能，优化与边界框的适配
        # ==============================================
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)
        # ==============================================
        # 5.1 tool面板：保持功能，优化与边界框的适配
        # ==============================================
        self.tool_panel = ToolPanel(simulation_view=self)
        self.tool_panel.setMaximumHeight(200)
        main_layout.addWidget(self.tool_panel)


        # ==============================================
        # 6. PyBullet容器：弱化内部边框，突出全局边界
        # ==============================================
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 内部容器仅加浅边框（避免与全局边界冲突），聚焦全局区分
        self.container.setStyleSheet("""
                    QWidget {
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        background-color: white;
                        padding: 5px;
                    }
                """)

        main_layout.addWidget(self.container)


        # layout.addWidget(self.container)

        # 确保容器窗口已创建
        self.container.winId()
        self.container.show()




        # # 启动PyBullet仿真
        # self.pybullet_process = PyBulletProcess()
        # self.pybullet_process.start()
        # self.env_loop = self.pybullet_process.loop

        # 初始化嵌入工具
        self.embedder = PyBulletEmbedder(self.container,self.pybullet_process.env_title)

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

    # 连接控制面板信号
    def connect_control_signals(self):
        self.control_panel.start_simulation.connect(self.on_control_panel_start_simulation)
        self.control_panel.stop_simulation.connect(self.on_control_panel_stop_simulation)
        self.control_panel.reset_simulation.connect(self.on_control_panel_reset_simulation)
        # self.control_panel.reset_simulation.connect(self.pybullet_process.env.clear_env)
        # self.control_panel.reset_simulation.connect(self.pybullet_process.env.load_scene)
        # self.control_panel.set_gravity.connect(self.set_gravity)
        # self.control_panel.set_time_step.connect(self.set_time_step)
        self.control_panel.show_axis_changed.connect(self.on_show_axis_changed)

    def on_control_panel_start_simulation(self):
        """处理控制面板的仿真状态变化"""
        asyncio.run_coroutine_threadsafe(self.pybullet_process.env.start_simulation(),self.env_loop)

    def on_control_panel_stop_simulation(self):
        """处理控制面板的仿真状态变化"""

        asyncio.run_coroutine_threadsafe(self.pybullet_process.env.stop_simulation(),self.env_loop)

    def on_control_panel_reset_simulation(self):
        """处理控制面板的仿真状态变化"""
        asyncio.run_coroutine_threadsafe(self.pybullet_process.env.clear_env(),self.env_loop)
        asyncio.run_coroutine_threadsafe(self.pybullet_process.env.load_scene(),self.env_loop)

    def on_show_axis_changed(self, ifshow: bool):
        """处理显示坐标轴状态变化"""
        # loop = self.pybullet_process.loop  # 获取 PyBulletProcess 的事件循环
        asyncio.run_coroutine_threadsafe(self.pybullet_process.env.show_axis(ifshow=ifshow), self.env_loop)


    def find_and_embed_pybullet(self):
        """嵌入PyBullet窗口"""
        if self.embedder.embed_window():
            self.label.setText("PyBullet simulation running")
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
        self.update_timer.stop()

        # 恢复PyBullet窗口
        self.embedder.restore_window()
        self.embedder.close()

        # 停止仿真
        self.pybullet_process.stop()
        self.pybullet_process.wait()

        super().closeEvent(event)



class ControlPanel(QWidget):
    """仿真控制面板"""

    # 定义信号
    start_simulation = pyqtSignal()
    stop_simulation = pyqtSignal()
    reset_simulation = pyqtSignal()
    set_gravity = pyqtSignal(float)
    set_time_step = pyqtSignal(float)
    show_axis_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 按钮样式：保持与全局风格统一（圆角+颜色区分）
        btn_style = """
            /* 1. 基础样式（所有状态共享：圆角、内边距、字体） */
            QPushButton {
                font-size: 13px;
                padding: 3px 8px;
                border: none;
                border-radius: 6px;
                color: white;  /* 启用时文字白色 */

            }

            /* 2. 启用状态 - 功能色区分（原有逻辑保留） */
            QPushButton#StartBtn { background-color: #22c55e; }  /* 开始：绿色 */
            QPushButton#StopBtn { background-color: #ef4444; }   /* 停止：红色 */
            QPushButton#ResetBtn { background-color: #f59e0b; }  /* 重置：橙色 */
            QPushButton#AxisBtn { background-color: #3b82f6; }   /* 坐标轴：蓝色 */

            /* 3.  hover状态（启用时）- 加深颜色，提示可交互 */
            QPushButton#StartBtn:hover:enabled { background-color: #16a34a; }  /* 深绿 */
            QPushButton#StopBtn:hover:enabled { background-color: #dc2626; }   /* 深红 */
            QPushButton#ResetBtn:hover:enabled { background-color: #d97706; }  /* 深橙 */
            QPushButton#AxisBtn:hover:enabled { background-color: #2563eb; }   /* 深蓝 */

            /* 4. 禁用状态 - 灰度化+文字色调整，强化不可交互感 */
            QPushButton:disabled {
                background-color: #e5e7eb;  /* 浅灰色背景（去饱和，无功能色） */
                color: #6b7280;             /* 深灰色文字（避免白色在浅灰上看不清） */
                opacity: 1;                 /* 取消透明度，用颜色区分更清晰（可选） */

            }
        """

        # 创建控制按钮
        self.start_btn = QPushButton("开始仿真")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setStyleSheet(btn_style)
        self.stop_btn = QPushButton("停止仿真")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setStyleSheet(btn_style)
        self.reset_btn = QPushButton("重置仿真")
        self.reset_btn.setObjectName("ResetBtn")
        self.reset_btn.setStyleSheet(btn_style)
        self.show_axis_btn = QPushButton("显示坐标轴")
        self.show_axis_btn.setObjectName("AxisBtn")
        self.show_axis_btn.setStyleSheet(btn_style)

        # 设置按钮状态
        self.stop_btn.setEnabled(False)
        self.show_axis_btn.setCheckable(False)

        # 连接信号
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.reset_btn.clicked.connect(self._on_reset)
        self.show_axis_btn.clicked.connect(self._on_show_axis)


        # 创建参数控制
        self.gravity_label = QLabel("重力:")
        self.gravity_spin = QDoubleSpinBox()
        self.gravity_spin.setRange(-20.0, 0.0)
        self.gravity_spin.setValue(-9.8)
        self.gravity_spin.setSingleStep(0.1)
        self.gravity_spin.valueChanged.connect(self._on_gravity_changed)

        self.timestep_label = QLabel("时间步长:")
        self.timestep_spin = QDoubleSpinBox()
        self.timestep_spin.setRange(0.001, 0.1)
        self.timestep_spin.setValue(0.01)
        self.timestep_spin.setSingleStep(0.001)
        self.timestep_spin.valueChanged.connect(self._on_timestep_changed)

        # 添加到布局
        self.layout.addWidget(self.start_btn)
        self.layout.addWidget(self.stop_btn)
        self.layout.addWidget(self.reset_btn)
        self.layout.addWidget(self.show_axis_btn)
        self.layout.addWidget(self.gravity_label)
        self.layout.addWidget(self.gravity_spin)
        self.layout.addWidget(self.timestep_label)
        self.layout.addWidget(self.timestep_spin)

        # 添加拉伸因子
        self.layout.addStretch(1)

    def _on_start(self):
        """处理开始仿真按钮点击"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_simulation.emit()

    def _on_stop(self):
        """处理停止仿真按钮点击"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_simulation.emit()

    def _on_reset(self):
        """处理重置仿真按钮点击"""
        self.reset_simulation.emit()

    def _on_gravity_changed(self, value):
        """处理重力值变化"""
        self.set_gravity.emit(value)

    def _on_timestep_changed(self, value):
        """处理时间步长变化"""
        self.set_time_step.emit(value)

    def update_status(self, is_running):
        """更新按钮状态"""
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)

    def _on_show_axis(self, ):
        """设置显示坐标轴按钮状态"""
        if self.show_axis_btn.text() == "显示坐标轴":
            self.show_axis_btn.setText("隐藏坐标轴")
            self.show_axis_changed.emit(True)
        else:
            self.show_axis_btn.setText("显示坐标轴")
            self.show_axis_changed.emit(False)


