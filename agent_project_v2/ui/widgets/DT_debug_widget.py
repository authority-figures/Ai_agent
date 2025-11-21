import math
from typing import List, Optional
from xml.etree import ElementTree as ET
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QHeaderView, QDialog, QTableWidget, QTableWidgetItem,QMessageBox, QInputDialog,
    QLabel, QDoubleSpinBox, QPushButton, QTextEdit, QRadioButton, QButtonGroup, QListWidget, QAction, QMenu, QFileDialog
)
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QColor
import asyncio
import logging

import pybullet as p

# 这里假设你已经有 DigitalTwinEnv 类
# from execution.simulation.digital_twin_env import DigitalTwinEnv


class RobotDebugWidget(QWidget):
    """
    用于在 DT 视图中手动调试机械臂的调试面板：
    - 获取仿真环境中机械臂关节信息
    - 使用 JointMove 运动到目标关节状态
    - 使用“位置伺服”执行一条关节路径（path）
    """
    def __init__(self, sim_view,DT_view, parent: Optional[QWidget] = None):
        """
        :param dt_env: DigitalTwinEnv 实例（里面有 physics_client 和 robot_list）
        """
        super().__init__(parent)
        self.sim_view = sim_view
        self.DT_view = DT_view



        # 为了 UI 简洁，可以只操作前 6 轴，超过部分你可以按需扩展
        self.num_joints_to_show = 6

        self.current_joint_boxes: List[QDoubleSpinBox] = []
        self.target_joint_boxes: List[QDoubleSpinBox] = []

        self._build_ui()

    # ------------------------------------------------------------------ UI 搭建
    def _build_ui(self):
        self.layout = QVBoxLayout(self)

        self.create_joint_move_work_bench()
        self.create_path_work_bench()


    # ------------------------------------------------------------------ 业务逻辑


    def create_joint_move_work_bench(self):
        """
            创建一行 JointMove 工具条：
            [ JointMove按钮 ] [ J1..J6 可编辑关节角 ] [ 复制仿真状态按钮 ]
            关节角单位使用“度”，方便人看。
            """
        row_widget = QWidget(self)
        layout = QHBoxLayout(row_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. 左侧 JointMove 按钮
        self.btn_joint_move = QPushButton("JointMove", row_widget)
        self.btn_joint_move.setFixedWidth(100)
        self.btn_joint_move.clicked.connect(self.on_joint_move_clicked)
        layout.addWidget(self.btn_joint_move)

        # 2. 中间 J1..J6 的可编辑关节角
        self.joint_spinboxes = []  # 保存起来后面要用
        joint_limits_rad = [
            (-2 * math.pi, 2 * math.pi),  # J1: [-360°, 360°]
            (-math.radians(125), math.radians(125)),  # J2: [-125°, 125°]
            (-math.radians(130), math.radians(130)),  # J3: [-130°, 130°]
            (-2 * math.pi, 2 * math.pi),  # J4: [-360°, 360°]
            (-math.radians(120), math.radians(120)),  # J5: [-120°, 120°]
            (-2 * math.pi, 2 * math.pi),  # J6: [-360°, 360°]
        ]
        for i in range(6):
            lbl =  QLabel(f"J{i + 1} (rad):", row_widget)
            layout.addWidget(lbl)

            spin = QDoubleSpinBox(row_widget)

            low, high = joint_limits_rad[i]
            spin.setRange(low, high)  # 直接用弧度范围
            spin.setDecimals(4)  # 弧度一般给 4 位小数比较实用
            # 不再需要角度后缀
            # spin.setSuffix("°")              # ← 去掉这行
            spin.setSingleStep(0.01)  # 一次步进 0.01 rad，大约 0.57°
            spin.setAlignment(Qt.AlignRight)

            layout.addWidget(spin)
            self.joint_spinboxes.append(spin)


        # 3. 右侧“复制仿真状态”按钮
        self.btn_copy_from_sim = QPushButton("Copy From Sim", row_widget)
        self.btn_copy_from_sim.setFixedWidth(130)
        self.btn_copy_from_sim.clicked.connect(self.on_copy_from_sim_clicked)
        layout.addWidget(self.btn_copy_from_sim)

        layout.addStretch(1)  # 右侧留点弹性空间

        self.layout.addWidget(row_widget)

    def create_path_work_bench(self):

        self.paths_dict = {}

        self.xml_group_box = QGroupBox("XML work bench")
        Vlayout = QVBoxLayout(self.xml_group_box)
        Hlayout = QHBoxLayout()
        Hlayout1 = QHBoxLayout()

        # 创建按钮组
        self.importXmlButton = QPushButton("Import XML")
        self.importXmlButton.clicked.connect(self.import_xml)
        self.pathsListWidget = QListWidget()
        Vlayout.addLayout(Hlayout1)
        Vlayout.addWidget(self.importXmlButton)
        Vlayout.addLayout(Hlayout)
        Hlayout.addWidget(self.pathsListWidget)
        Vlayout1 = QVBoxLayout()
        self.showPathButton = QPushButton("Show Path Data")
        self.showPathButton.clicked.connect(self.show_selected_path)

        Vlayout1.addWidget(self.showPathButton)
        Hlayout.addLayout(Vlayout1)
        self.remove_path_action = QAction('Remove')
        self.pathsListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.remove_path_action.triggered.connect(self.remove_selected_path)
        self.rename_path_action = QAction('Rename', self)
        self.rename_path_action.triggered.connect(self.rename_selected_path)

        self.pathsListWidget.customContextMenuRequested.connect(self.create_path_context_menu)

        self.layout.addWidget(self.xml_group_box)
        pass

    def on_joint_move_clicked(self):
        """
        读取 J1..J6 输入框的角度（deg），转换为 rad，
        在仿真中直接把关节状态 reset 到目标位置。
        后面你可以替换为更平滑的插补控制。
        """

        try:
            if not hasattr(self, "DT_view") or self.sim_view is None:
                print("[JointMoveBench] DT_view not set.")
                return
            if not self.DT_view.robot_api:
                print("[JointMoveBench] No robot_api in DT_view.")
                return

            # 1. 读取目标角度
            target_rad = [spin.value() for spin in self.joint_spinboxes]

            asyncio.run_coroutine_threadsafe(self.DT_view.robot_api.joint_move(target_rad),self.DT_view.loop)


            print("[JointMoveBench] JointMove in simulation done. target(rad) =", target_rad)

        except Exception as e:
            print(f"[JointMoveBench:on_joint_move_clicked] Error: {e}")

    def on_copy_from_sim_clicked(self):
        """
        从 DigitalTwinEnv 中读取当前仿真机械臂关节角（rad），
        转换成度填进 J1..J6 输入框。
        """
        try:
            if not hasattr(self, "sim_view") or self.sim_view is None:
                print("[JointMoveBench] sim_env not set.")
                return
            if not hasattr(self.sim_view.tool_panel.arm_tool_page,"GUI_joints_angle_data") or self.sim_view.tool_panel.arm_tool_page.GUI_joints_angle_data is None:
                print("[JointMoveBench] 请打开仿真环境的机械臂状态订阅器.")
                return

            joints_text = self.sim_view.tool_panel.arm_tool_page.GUI_joints_angle_data.text()
            angles_str_list = [s.strip() for s in joints_text.split(',')]
            if not all(angles_str_list):
                print("[JointMoveBench] 仿真环境的机械臂状态数据不正确，请打开.")
                logging.info("[JointMoveBench] 仿真环境的机械臂状态数据不正确，请打开.")
                return
            joint_angles = list(map(float, angles_str_list))
            for i, spin in enumerate(self.joint_spinboxes):
                joint_deg = joint_angles[i]
                spin.setValue(joint_deg)
            print("[JointMoveBench] Copied joint state from simulation.")
            logging.info("[JointMoveBench] Copied joint state from simulation.")
        except Exception as e:
            print(f"[JointMoveBench:on_copy_from_sim_clicked] Error: {e}")
            logging.info(f"[JointMoveBench:on_copy_from_sim_clicked] Error: {e}")

    def create_remove_path(self, position):
        item = self.pathsListWidget.itemAt(position)
        menu = QMenu()
        if item is not None:
            menu.addAction(self.remove_path_action)
            menu.exec_(self.pathsListWidget.mapToGlobal(position))

    def remove_selected_path(self):
        item = self.pathsListWidget.currentItem()
        if item is None:
            return

        name = item.text()

        # 从 dict 中删
        if name in self.paths_dict:
            del self.paths_dict[name]

        # 从列表控件中删
        row = self.pathsListWidget.row(item)
        self.pathsListWidget.takeItem(row)

        logging.info(f"Removed path: {name}")

    def rename_selected_path(self):
        item = self.pathsListWidget.currentItem()
        if item is None:
            return

        old_name = item.text()

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Path",
            "Input new name:",
            text=old_name
        )

        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            return

        # 检查是否重名（且不是自己）
        if new_name in self.paths_dict and new_name != old_name:
            QMessageBox.warning(self, "Name Exists", f"Path '{new_name}' already exists.")
            return

        # 更新 dict
        if old_name in self.paths_dict:
            path_data = self.paths_dict.pop(old_name)
            self.paths_dict[new_name] = path_data

        # 更新列表显示
        item.setText(new_name)

        logging.info(f"Renamed path: {old_name} -> {new_name}")

    def show_selected_path(self):
        selected_item = self.pathsListWidget.currentItem()
        if selected_item:
            path_name = selected_item.text()
            path_data = self.paths_dict[path_name]  # list
            # Create and show the dialog
            dialog = PathDataDialog(path_data, path_name, self.sim_view, self)
            dialog.show()

    def import_xml(self):
        default_dir = '/home/lwh/Project/python_project/Ai_agent/agent_project_v2/assets/datas/test_datas'
        filename, _ = QFileDialog.getOpenFileName(self, "Open XML file", default_dir, "XML files (*.xml)")
        if filename:
            self.parse_xml(filename, )
            logging.info(f"Imported XML file: {filename}")


    def parse_xml(self, filename, ):
        tree = ET.parse(filename)
        root = tree.getroot()
        path = []  # Initialize a new path list

        path_name = root.get('name', f'Unnamed{len(self.paths_dict) + 1}')  # Default or provided name

        for step in root.findall('Point'):
            joints = [float(step.find(f'Joint{i}').text) for i in range(1, 7)]
            path.append(tuple(joints))

        self.paths_dict[path_name] = path
        self.pathsListWidget.addItem(path_name)  # Add path name to the list widget


    def create_path_context_menu(self, position):
        item = self.pathsListWidget.itemAt(position)
        if item is None:
            return

        # 先把当前项选中，方便后面用 currentItem()
        self.pathsListWidget.setCurrentItem(item)

        menu = QMenu(self)
        menu.addAction(self.remove_path_action)
        menu.addAction(self.rename_path_action)
        menu.exec_(self.pathsListWidget.mapToGlobal(position))


class PathDataDialog(QDialog):
    def __init__(self, path_data, path_name, sim_view, parent=None):
        super().__init__(parent)

        self.path_data = path_data
        self.sim_view = sim_view

        self.setWindowTitle(f"Data for {path_name}")
        self.resize(900, 600)  # Adjust size as needed

        layout = QVBoxLayout(self)


        # Create a table widget
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(len(path_data))
        # Add one more column for step indices
        self.tableWidget.setColumnCount(7)  # Now 7 columns including the step column
        headers = ["Point"] + [f"Joint {i + 1}" for i in range(6)]
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)

        # === 关键：右键菜单策略 ===
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.on_table_context_menu)

        # Populate the table
        for i, angles in enumerate(path_data):
            # Insert the step index
            step_item = QTableWidgetItem(f"point:{str(i)}")
            step_item.setTextAlignment(Qt.AlignCenter)
            step_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.tableWidget.setItem(i, 0, step_item)

            # Insert angles
            for j, angle in enumerate(angles):
                item = QTableWidgetItem(f"{angle:.5f}")
                item.setTextAlignment(Qt.AlignCenter)
                if j % 2 == 0:
                    item.setBackground(QColor(220, 220, 220))  # Light gray
                else:
                    item.setBackground(QColor(245, 245, 245))  # Very light gray
                self.tableWidget.setItem(i, j + 1, item)

        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tableWidget)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def show(self):
        self.tableWidget.resizeColumnsToContents()  # Resize columns to fit content
        super().show()

        # ------------------------------------------------------------------
        # 右键菜单回调
        # ------------------------------------------------------------------
    def on_table_context_menu(self, pos: QPoint):
        """在 table 上右键时调用"""
        # 找到鼠标所在行的 item
        item = self.tableWidget.itemAt(pos)
        if item is None:
            return

        # 把这行选中
        row = item.row()
        self.tableWidget.selectRow(row)

        menu = QMenu(self)

        # 创建“设置到仿真机械臂”动作
        set_to_sim_action = QAction("设置到仿真机械臂", self)
        set_to_sim_action.triggered.connect(lambda: self.apply_row_to_simulation(row))
        menu.addAction(set_to_sim_action)

        menu.exec_(self.tableWidget.mapToGlobal(pos))

    def apply_row_to_simulation(self, row: int):
        """
        将指定行的 joints 设置到仿真环境中的机械臂上
        默认认为 path_data 中的值就是弧度（rad）
        """
        if self.sim_view is None:
            print("[PathDataDialog] sim_view is None, cannot apply to simulation.")
            return
        # 从 path_data 里取 joints（保证和表格一致）
        if row < 0 or row >= len(self.path_data):
            print(f"[PathDataDialog] invalid row index: {row}")
            return

        joints = self.path_data[row]

        asyncio.run_coroutine_threadsafe(
            self.sim_view.pybullet_process.env.joint_move(joints),
            self.sim_view.env_loop)

        print(f"[PathDataDialog] Applied row {row} joints to simulation: {joints}")









if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # 这里你需要传入一个 DigitalTwinEnv 实例
    dt_env = None  # TODO: 创建并初始化 DigitalTwinEnv 实例

    widget = RobotDebugWidget(dt_env,None)
    widget.resize(400, 600)
    widget.show()

    sys.exit(app.exec_())