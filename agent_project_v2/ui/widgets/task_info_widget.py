from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QGroupBox, QTextEdit, QPushButton, QFrame,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import sys


# ==============================================================
# 子组件：Step详情窗口
# ==============================================================
class StepDetailWidget(QGroupBox):
    """封装 Step 详情区（进度 + 运行视图 + 日志）"""
    def __init__(self, parent=None):
        super().__init__("当前 Step 详情", parent)

        layout = QVBoxLayout()
        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)

        self.step_display = QFrame()
        self.step_display.setFrameShape(QFrame.StyledPanel)
        self.step_display.setMinimumHeight(150)

        self.step_log = QTextEdit()
        self.step_log.setReadOnly(True)

        layout.addWidget(QLabel("当前Step进度"))
        layout.addWidget(self.step_progress)
        layout.addWidget(QLabel("Step运行视图"))
        layout.addWidget(self.step_display)
        layout.addWidget(QLabel("Step日志"))
        layout.addWidget(self.step_log)

        self.setLayout(layout)

    def update_step_detail(self, task,step_id):
        """更新 Step 信息（标题、进度、日志）"""
        step = next((s for s in task["plan"] if s["id"] == step_id), None)
        progress = task.get("progress", {})
        self.setTitle(f"Step详情 - {step['action']}")
        step_status = None if not progress else progress.get("step_status", {})
        if not step_status:
            # print("[task_info_widget][show_task_detail]无步骤状态数据")
            step_status = {}

        step_state = step_status.get(step["id"], "pending")
        progress = (
            100 if step_state == "ok"
            else 50 if step_state == "running"
            else 0
        )
        self.step_progress.setValue(progress)
        self.step_log.setText(
            f"当前Step：{step['id']}\n"
            f"描述：{step['action']}\n"
            f"状态：{step_state}\n"
            f"日志：\n- 执行正常...\n- 等待下一步..."
        )

    def reset(self):
        """清空 Step 信息"""
        self.setTitle("当前 Step 详情")
        self.step_progress.setValue(0)
        self.step_log.setText("暂无 Step 信息。")


# ==============================================================
# Step 按钮组件
# ==============================================================
class StepButton(QPushButton):
    """自定义Step按钮，用颜色区分状态"""
    clicked_with_id = pyqtSignal(str)

    def __init__(self, step_id, desc, status="pending"):
        super().__init__(step_id)
        self.step_id = step_id
        self.desc = desc
        self.status = status
        self.update_color()
        self.clicked.connect(self._emit_id)

    def _emit_id(self):
        self.clicked_with_id.emit(self.step_id)

    def update_color(self):
        if self.status == "ok":
            color = QColor("#4CAF50")  # 绿色
        elif self.status == "running":
            color = QColor("#2196F3")  # 蓝色
        else:
            color = QColor("#B0BEC5")  # 灰色

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                color: white;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #64B5F6;
            }}
        """)


# ==============================================================
# 主窗口：任务信息窗口
# ==============================================================
class TaskInfoWidget(QWidget):
    def __init__(self,tasks: list[dict]=None):
        super().__init__()
        self.tasks = tasks  # 任务数据列表
        self.setWindowTitle("任务信息窗口")
        self.resize(1000, 600)
        self.setWindowFlag(Qt.Window)

        main_layout = QHBoxLayout(self)

        # ===== 左侧任务表 =====
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels(["Task ID", "名称", "状态"])
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.cellClicked.connect(self.on_task_selected)

        # ===== 右侧详情区 =====
        right_layout = QVBoxLayout()

        # --- Task 概览 ---
        self.label_task_info = QLabel("请选择任务以查看详细信息。")
        self.label_task_info.setWordWrap(True)
        group_task = QGroupBox("任务概览")
        vbox_task = QVBoxLayout()
        vbox_task.addWidget(self.label_task_info)
        group_task.setLayout(vbox_task)

        # --- Plan 执行进度 ---
        group_plan = QGroupBox("Plan 执行进度")
        vbox_plan = QVBoxLayout()
        self.step_layout = QHBoxLayout()
        vbox_plan.addLayout(self.step_layout)
        group_plan.setLayout(vbox_plan)

        # --- Step详情组件（封装类） ---
        self.step_detail_widget = StepDetailWidget()

        right_layout.addWidget(group_task)
        right_layout.addWidget(group_plan)
        right_layout.addWidget(self.step_detail_widget)

        main_layout.addWidget(self.task_table, 3)
        main_layout.addLayout(right_layout, 6)

        # ===== 数据填充 =====
        self.update_tasks()
        # self.load_sample_data()

    def update_tasks(self, ):
        if not self.tasks:
            print("[task_info_widget][update_tasks]任务表组件未初始化")
            return

        self.task_table.setRowCount(len(self.tasks))
        for i, t in enumerate(self.tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(t["task_id"]))
            self.task_table.setItem(i, 1, QTableWidgetItem(t["task_name"]))
            self.task_table.setItem(i, 2, QTableWidgetItem(t["status"]))

        pass

    def load_sample_data(self):
        """虚拟任务数据"""
        self.tasks = [
            {
                "id": "t-001",
                "name": "加载机械臂",
                "status": "执行中",
                "steps": [
                    {"id": "step-1", "desc": "确认机械臂型号", "status": "done"},
                    {"id": "step-2", "desc": "准备设备", "status": "done"},
                    {"id": "step-3", "desc": "安装机械臂", "status": "running"},
                    {"id": "step-4", "desc": "初步测试", "status": "pending"},
                    {"id": "step-5", "desc": "记录结果", "status": "pending"},
                ],
            },
            {
                "id": "t-002",
                "name": "轨迹优化测试",
                "status": "待执行",
                "steps": [],
            }
        ]

        self.task_table.setRowCount(len(self.tasks))
        for i, t in enumerate(self.tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(t["id"]))
            self.task_table.setItem(i, 1, QTableWidgetItem(t["name"]))
            self.task_table.setItem(i, 2, QTableWidgetItem(t["status"]))

    def activate_task(self, task_id: str):
        """激活并显示指定任务"""
        for row in range(self.task_table.rowCount()):
            if self.task_table.item(row, 0).text() == task_id:
                self.task_table.selectRow(row)
                self.show_task_detail(task_id)
                self.on_task_selected(row, 0)
                break

    def on_task_selected(self, row, col):
        task_id = self.task_table.item(row, 0).text()
        self.show_task_detail(task_id)

    def show_task_detail(self, task_id):
        """显示任务详细信息与步骤"""
        task = next((t for t in self.tasks if t["task_id"] == task_id), None)
        if not task:
            return

        self.label_task_info.setText(
            f"<b>ID：</b>{task['task_id']}<br>"
            f"<b>任务名：</b>{task['task_name']}<br>"
            f"<b>状态：</b>{task['status']}"
        )

        # 清空旧按钮
        while self.step_layout.count():
            item = self.step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        plan_steps = task.get("plan", {})
        if not plan_steps:
            self.step_detail_widget.reset()
            print("[task_info_widget][show_task_detail]无步骤数据")
            return
        progress = task.get("progress", {})
        step_status = None if not progress else progress.get("step_status", {})

        if not step_status:
            # print("[task_info_widget][show_task_detail]无步骤状态数据")
            step_status = {}



        # 创建新 Step 按钮
        for pls in plan_steps:
            step_state = step_status.get(pls["id"], "pending")
            btn = StepButton(pls["id"], pls["action"], step_state)
            btn.clicked_with_id.connect(self.show_step_detail)
            self.step_layout.addWidget(btn)

        # 自动显示第一个 Step
        if plan_steps:
            self.show_step_detail(plan_steps[0]["id"])
        else:
            self.step_detail_widget.reset()

    def show_step_detail(self, step_id):
        """显示指定 Step 详情"""
        for task in self.tasks:
            for s in task["plan"]:
                if s["id"] == step_id:
                    step = s
                    self.step_detail_widget.update_step_detail(task,step_id)
                    return
        self.step_detail_widget.reset()


# ==============================================================
# 调试入口
# ==============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TaskInfoWidget()
    w.show()
    sys.exit(app.exec_())
