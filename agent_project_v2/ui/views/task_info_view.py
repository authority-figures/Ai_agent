import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QPushButton, QMenu
)
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QSize  # ✅ 添加 QSize
from ui.widgets.task_info_widget import TaskInfoWidget
import asyncio
import httpx
from PyQt5.QtCore import QThread, pyqtSignal
import requests

class FetchTasksThread(QThread):
    '''
    后台线程：同步获取任务列表
    '''
    # 定义一个信号，用于传递获取到的数据
    finished = pyqtSignal(list)

    def run(self):
        # 这里用 requests 同步请求 API
        import requests
        r = requests.get("http://127.0.0.1:8000/api/tasks")
        data = r.json()
        self.finished.emit(data)


class TaskItemWidget(QWidget):
    def __init__(self, name, status):
        super().__init__()
        self.name = name
        self.status = status

        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(name)
        font = QFont()
        font.setPointSize(12)  # 修改文字大小
        self.label.setFont(font)
        layout.addWidget(self.label)

        # 设置背景颜色和透明度
        color = self._get_color_for_status(status)
        r, g, b = color.red(), color.green(), color.blue()
        alpha = 180  # 透明度 0-255
        self.setStyleSheet(f"background-color: rgba({r},{g},{b},{alpha}); border-radius: 0px;")

    def _get_color_for_status(self, status):
        if status == "done":
            return QColor("#4CAF50")  # 绿色
        elif status == "running":
            return QColor("#2196F3")  # 蓝色
        else:
            return QColor("#B0BEC5")  # 灰色



class TaskInfoView(QWidget):
    def __init__(self, tasks: list[dict]=None, parent=None):
        super().__init__(parent)
        self.tasks = tasks  # [{id, name, status, steps: [...]}, ...]
        if self.tasks is None:
            self.load_sample_data()
        # self.task_widgets = {}  # 存储打开的 TaskInfoWidget
        self.task_info_widget : TaskInfoWidget|None = None  # 用于存储 TaskInfoWidget 实例

        # --- 布局 ---
        layout = QVBoxLayout(self)
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新任务")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        layout.addWidget(self.refresh_btn)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # 允许自定义右键菜单
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)

        # --- 初始化任务列表 ---
        self.populate_task_list()
        self.list_widget.itemClicked.connect(self.on_task_clicked)

    async def refresh_tasks(self):
        """从 API 获取最新任务并刷新列表"""
        url = "http://127.0.0.1:8000/api/tasks"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url)  # 需要实现获取所有任务的 API
                r.raise_for_status()
                tasks_data = r.json()  # 假设返回格式：[{id,name,status,steps:[...]}, ...]

            self.tasks = tasks_data
            self.populate_task_list()
        except Exception as e:
            print(f"[TaskInfoView] 刷新任务失败: {e}")

    def on_refresh_clicked(self):
        self.thread = FetchTasksThread()
        self.thread.finished.connect(self.on_tasks_fetched)
        self.thread.start()

    def on_tasks_fetched(self, tasks):
        self.tasks = tasks
        if self.task_info_widget:
            self.task_info_widget.tasks = tasks
            self.task_info_widget.update_tasks()
        self.populate_task_list()
        self.thread = None

    def populate_task_list(self):
        """加载任务名称与状态颜色"""
        self.list_widget.clear()
        for task in self.tasks:
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 40))  # 控制item高度
            item.setData(Qt.UserRole, task)  # ✅ 保存整个任务对象
            widget = TaskItemWidget(task["task_name"], task["status"])
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)



    def on_task_clicked(self, item: QListWidgetItem):
        """点击任务时打开详细窗口"""
        task_id = item.data(Qt.UserRole).get("task_id")
        if not task_id:
            print("[task_info_view:on_task_clicked]⚠️ 无效任务ID")
            return
        if self.task_info_widget is None:
            self.task_info_widget = TaskInfoWidget(self.tasks)
        self.task_info_widget.activate_task(task_id)
        self.task_info_widget.show()
        self.task_info_widget.raise_()  # 保证窗口在最前

        # ------------------ 右键菜单 ------------------

    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return

        menu = QMenu()
        delete_action = menu.addAction("删除任务")
        delete_redis_action = menu.addAction("删除Redis数据（慎用）")
        action = menu.exec_(self.list_widget.mapToGlobal(pos))

        if action == delete_action:
            self.delete_task(item)
        elif action == delete_redis_action:
            self.delete_task_redis_sync(item)   # qt槽函数的触发不能是协程函数,只能使用同步函数

    def delete_task(self, item: QListWidgetItem):
        task = item.data(Qt.UserRole)
        if task is None:
            return
        task_id = task.get("task_id")
        if not task_id:
            return

        # 如果 TaskInfoWidget 正在显示这个任务，需要重置
        # if self.task_info_widget:
        #     if self.task_info_widget.current_task_id == task_id:
        #         self.task_info_widget.reset()

        # 从本地列表中删除
        self.tasks = [t for t in self.tasks if t.get("task_id") != task_id]

        # 刷新列表
        self.populate_task_list()

    def delete_task_redis_sync(self, item: QListWidgetItem):
        task = item.data(Qt.UserRole)
        if task is None:
            return
        task_id = task.get("task_id")
        if not task_id:
            return

        url = f"http://127.0.0.1:8000/api/tasks/{task_id}"
        try:
            resp = requests.delete(url)
            if resp.status_code == 200:
                print(f"✅ 删除成功: {resp.json()['message']}")
            else:
                print(f"❌ 删除失败: {resp.text}")

            self.on_refresh_clicked()

        except Exception as e:
            print(f"[TaskInfoView] 删除任务失败: {e}")

    async def delete_task_redis(self, item: QListWidgetItem):
        task = item.data(Qt.UserRole)
        if task is None:
            return
        task_id = task.get("task_id")
        if not task_id:
            return

        """从 API 获取最新任务并刷新列表"""
        url = f"http://127.0.0.1:8000/api/tasks/{task_id}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(url)  # 需要实现获取所有任务的 API
                status_code = resp.raise_for_status()

                if status_code == 200:
                    print(f"✅ 删除成功: {resp.json()['message']}")
                else:
                    print(f"❌ 删除失败: {resp.text}")

            self.on_refresh_clicked()

        except Exception as e:
            print(f"[TaskInfoView] 刷新任务失败: {e}")




    def load_sample_data(self):
        """虚拟任务数据"""
        self.tasks = [
            {
                "task_id": "t-001",
                "task_name": "加载机械臂",
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
                "task_id": "t-002",
                "task_name": "轨迹优化测试",
                "status": "待执行",
                "steps": [],
            }
        ]


# --- 测试主函数 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 模拟任务数据
    tasks = [
        {
            "task_id": "t-001",
            "task_name": "加载机械臂",
            "status": "pending",
            "steps": [
                {"id": "step-1", "desc": "确认机械臂型号", "status": "done"},
                {"id": "step-2", "desc": "准备设备", "status": "done"},
                {"id": "step-3", "desc": "安装机械臂", "status": "running"},
                {"id": "step-4", "desc": "初步测试", "status": "pending"},
                {"id": "step-5", "desc": "记录结果", "status": "pending"},
            ],
        },
        {
            "task_id": "t-002",
            "task_name": "轨迹优化测试",
            "status": "running",
            "steps": [],
        }
    ]

    window = TaskInfoView(tasks)
    window.setWindowTitle("任务缩略信息视图")
    window.resize(400, 300)
    window.show()

    sys.exit(app.exec())
