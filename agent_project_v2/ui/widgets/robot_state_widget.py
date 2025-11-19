# 用于在DT窗口显示机械臂的详细信息

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QDialog, QScrollArea, QApplication
)
from PyQt5.QtCore import Qt
from typing import Dict, Any
# from .status_parser import parse_robot_status  # 如果拆成独立模块就这样导入


from typing import Any, Dict, List


def parse_robot_status(raw_status: List[Any]) -> Dict[str, Any]:
    """
    将 JAKA 的 robotstatus 列表解析为带字段名的 dict。
    注意：索引顺序基于你给的说明，如果 SDK 实际顺序有差异，按实际调整。
    """
    # 防御性处理
    if not isinstance(raw_status, (list, tuple)) or len(raw_status) < 24:
        return {}

    # 按你提供的字段顺序映射
    status = {
        "errcode":                 raw_status[0],
        "inpos":                   raw_status[1],
        "powered_on":              raw_status[2],
        "enabled":                 raw_status[3],
        "rapidrate":               raw_status[4],
        "protective_stop":         raw_status[5],
        "drag_status":             raw_status[6],
        "on_soft_limit":           raw_status[7],
        "current_user_id":         raw_status[8],
        "current_tool_id":         raw_status[9],
        "dout":                    raw_status[10],
        "din":                     raw_status[11],
        "aout":                    raw_status[12],
        "ain":                     raw_status[13],
        "tio_dout":                raw_status[14],
        "tio_din":                 raw_status[15],
        "tio_ain":                 raw_status[16],
        "extio":                   raw_status[17],
        "cart_position":           raw_status[18],  # 通常是 [x,y,z,rx,ry,rz]
        "joint_position":          raw_status[19],  # 通常是 6 或 7 轴角度
        "robot_monitor_data":      raw_status[20],
        "torq_sensor_monitor_data":raw_status[21],
        "is_socket_connect":       raw_status[22],
        "emergency_stop":          raw_status[23],
    }

    # 如果实际还有 tio_key（长度 25），可以这样兼容一下：
    if len(raw_status) > 24:
        status["tio_key"] = raw_status[24]

    return status


class RobotStatusDialog(QDialog):
    def __init__(self, status_dict: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Robot Status Details")
        self.resize(500, 600)

        main_layout = QVBoxLayout(self)

        # 用 QScrollArea 适配长内容
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        # 把 status_dict 全部展开显示
        for key, value in status_dict.items():
            # 把复杂结构转成字符串
            text = str(value)
            label_key = QLabel(key + ":")
            label_val = QLabel(text)
            label_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(label_key, label_val)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        btn_close = QPushButton("Close", self)
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignRight)



if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    sample_status = {
        "joint_positions": [0.0, 1.0, 0.5, -0.5, 0.2, 1.5],
        "joint_velocities": [0.01, 0.02, 0.01, -0.01, 0.005, 0.015],
        "end_effector_pose": {
            "position": [0.5, 0.3, 0.2],
            "orientation": [0.0, 0.707, 0.0, 0.707]
        },
        "gripper_state": "open",
        "errors": None
    }
    dialog = RobotStatusDialog(sample_status)
    dialog.exec_()