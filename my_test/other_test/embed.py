import sys
import os
import time
import subprocess
import threading
import pybullet as p
import pybullet_data
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QToolBar, QDockWidget)
from PyQt5.QtCore import QTimer, Qt, QProcess, QThread, QRect
from PyQt5.QtGui import QWindow
import Xlib
import Xlib.display
from Xlib import X

# 为PyBullet窗口设置唯一的名称
PYBULLET_WINDOW_NAME = "MyPyBulletSimulation_" + str(int(time.time()))


class PyBulletProcess(QThread):
    """运行PyBullet仿真的线程"""

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        # 连接物理引擎，设置窗口名称
        options = f"--window_title={PYBULLET_WINDOW_NAME} --width=800 --height=600"
        physics_client = p.connect(p.GUI, options=options)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.8)

        # 加载地面
        p.loadURDF("plane.urdf")

        # 添加一个立方体
        cube_start_pos = [0, 0, 1]
        cube_start_orientation = p.getQuaternionFromEuler([0, 0, 0])
        p.loadURDF("cube.urdf", cube_start_pos, cube_start_orientation)

        # 运行仿真
        while self.running:
            p.stepSimulation()
            time.sleep(1. / 240.)

        p.disconnect()

    def stop(self):
        self.running = False


class PyBulletEmbedder:
    """PyBullet窗口嵌入工具类"""

    def __init__(self, container_widget):
        self.container = container_widget
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.bullet_window_id = None
        self.container_window_id = int(container_widget.winId())

    def find_pybullet_window(self):
        """查找PyBullet窗口"""
        # 首先尝试使用xdotool查找窗口
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", PYBULLET_WINDOW_NAME],
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
                if name and PYBULLET_WINDOW_NAME in name:
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 状态标签
        self.label = QLabel("Initializing PyBullet simulation...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # 容器用于嵌入窗口
        self.container = QWidget(self)
        self.container.setMinimumSize(800, 600)
        layout.addWidget(self.container)

        # 确保容器窗口已创建
        self.container.winId()
        self.container.show()

        # 初始化嵌入工具
        self.embedder = PyBulletEmbedder(self.container)

        # 启动PyBullet仿真
        self.pybullet_process = PyBulletProcess()
        self.pybullet_process.start()

        # 设置定时器查找PyBullet窗口
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.find_and_embed_pybullet)
        self.timer.start(1000)  # 每1000毫秒检查一次，给PyBullet更多时间启动

        # 设置定时器更新窗口位置
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_window_position)
        self.update_timer.start(100)  # 每100毫秒更新一次位置

        # 仿真状态
        self.simulation_running = False

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


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyBullet Simulation Embedding")
        self.setGeometry(100, 100, 1200, 800)

        # 创建仿真视图
        self.simulation_view = SimulationView()

        # 创建停靠窗口
        dock = QDockWidget("Simulation", self)
        dock.setWidget(self.simulation_view)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # 创建工具栏
        self.create_toolbar()

        # 创建状态栏
        self.statusBar().showMessage("Ready")

        # 显示主窗口
        self.show()

    def create_toolbar(self):
        """创建仿真控制工具栏"""
        toolbar = QToolBar("Simulation Controls", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # 启动按钮
        start_btn = QPushButton("Start Simulation")
        start_btn.clicked.connect(self.start_simulation)
        toolbar.addWidget(start_btn)

        # 停止按钮
        stop_btn = QPushButton("Stop Simulation")
        stop_btn.clicked.connect(self.stop_simulation)
        toolbar.addWidget(stop_btn)

        # 重置按钮
        reset_btn = QPushButton("Reset Simulation")
        reset_btn.clicked.connect(self.reset_simulation)
        toolbar.addWidget(reset_btn)

    def start_simulation(self):
        """启动仿真"""
        self.statusBar().showMessage("Simulation started")

    def stop_simulation(self):
        """停止仿真"""
        self.statusBar().showMessage("Simulation stopped")

    def reset_simulation(self):
        """重置仿真"""
        self.statusBar().showMessage("Simulation reset")

    def resizeEvent(self, event):
        """处理主窗口大小变化"""
        super().resizeEvent(event)

        # 更新PyBullet窗口位置
        if hasattr(self, 'simulation_view'):
            self.simulation_view.update_window_position()

    def moveEvent(self, event):
        """处理主窗口移动事件"""
        super().moveEvent(event)

        # 更新PyBullet窗口位置
        if hasattr(self, 'simulation_view'):
            self.simulation_view.update_window_position()

    def closeEvent(self, event):
        """关闭窗口时的清理工作"""
        super().closeEvent(event)


if __name__ == '__main__':
    # 检查是否安装了xdotool
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        print("请安装xdotool: sudo apt-get install xdotool")
        sys.exit(1)

    # 创建应用实例
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()

    # 运行应用
    sys.exit(app.exec_())