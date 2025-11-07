import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QScrollArea,
    QHBoxLayout, QLabel, QScrollBar, QSizePolicy, QApplication
)
from PyQt5.QtGui import (QFont, QFontMetrics
                         )
from PyQt5.QtCore import Qt, pyqtSignal, QTimer


# ---------- 像素级手动折行 ----------
def break_long_text(text: str, font: QFont, max_px: int) -> str:
    """按像素宽度插入 \\n，模拟自动换行"""
    fm = QFontMetrics(font)
    out_lines = []
    for raw_line in text.splitlines():          # 保留原始手工换行
        if fm.width(raw_line) <= max_px:        # 整行够短，直接保留
            out_lines.append(raw_line)
            continue

        # 逐字符累加，超宽就切
        cur_width = 0
        cur_chunk = []
        for ch in raw_line:
            w = fm.width(ch)
            if cur_width + w > max_px and cur_chunk:  # 需要断开
                out_lines.append(''.join(cur_chunk))
                cur_chunk.clear()
                cur_width = 0
            cur_chunk.append(ch)
            cur_width += w
        if cur_chunk:               # 剩余不足一行
            out_lines.append(''.join(cur_chunk))
    return '\n'.join(out_lines)

def create_bubble(sender, message, bg_color, text_color, align_right=False):
    """创建一个带圆角的聊天气泡"""
    font = QApplication.font()  # 取全局字体
    max_px = 300  # 与 QLabel 最大宽度一致
    wrapped = break_long_text(message, font, max_px)

    bubble = QLabel(f"<b>{sender}:</b><br>{wrapped}")
    bubble.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            border-radius: 12px;
            padding: 8px 10px;
            font-size: 14px;
        """)
    bubble.setWordWrap(True)
    bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
    bubble.setMaximumWidth(max_px)
    bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

    # 用一个容器包装，用于左对齐或右对齐
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(5, 2, 5, 2)
    if align_right:
        layout.addStretch()
        layout.addWidget(bubble)
    else:
        layout.addWidget(bubble)
        layout.addStretch()
    return container

class AgentChatView(QWidget):
    """用于与Agent交互的对话视图（左对齐+气泡样式）"""
    messageSent = pyqtSignal(str)  # 用户发送消息信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgentChatView")
        self.msg_counter = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ===== 标题 =====
        title = QLabel("Agent Dialogue")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 16px; color: #2E3A59;")
        layout.addWidget(title)

        # ===== 聊天显示区 =====
        # 聊天内容容器
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #F6F6F6; border: none;")
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.chat_widget)

        # ===== 输入区 =====
        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message to the agent...")
        # self.input_field.setInputMethodHints(self.input_field.inputMethodHints() | Qt.ImhPreferLatin | Qt.ImhAllowLatin)
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #D0D7DE;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }
        """)
        input_layout.addWidget(self.input_field, stretch=4)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        input_layout.addWidget(send_button, stretch=1)
        layout.addWidget(self.scroll_area)
        layout.addLayout(input_layout)
        self.setLayout(layout)

    # ===== 发送消息 =====
    def send_message(self):
        user_text = self.input_field.text().strip()
        if not user_text:
            return

        self.append_message("User", user_text)
        self.input_field.clear()
        self.messageSent.emit(user_text)

    # ===== 添加消息到显示区 =====
    def append_message(self, sender, message):
        """以气泡样式追加聊天消息，所有消息左对齐"""
        self.msg_counter += 1
        index_text = f"[{self.msg_counter}]"
        full_send_text = f"{index_text} {sender}"
        if sender == "Agent" or sender == "System":
            bubble_color = "#B2F199"   # 浅蓝背景
            text_color = "#1E3A8A"
            bubble = create_bubble(full_send_text, message, bubble_color, text_color, align_right=False)
        else:  # User
            bubble_color = "#FCFDD0"
            text_color = "#14010E"
            bubble = create_bubble(full_send_text, message, bubble_color, text_color, align_right=True)

        self.chat_layout.addWidget(bubble)

        # 自动滚动到底部
        self.scroll_to_bottom()
        # self.scroll_area.verticalScrollBar().setValue(
        #     self.scroll_area.verticalScrollBar().maximum()
        # )


    def create_bubble(sender, message, bg_color, text_color):
        bubble = QLabel(f"<b>{sender}:</b><br>{message}")
        bubble.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            border-radius: 12px;
            padding: 8px 10px;
        """)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return bubble

    def scroll_to_bottom(self):
        self.chat_widget.adjustSize()
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))



from PyQt5.QtCore import QThread, pyqtSignal
import requests

class AgentWorker(QThread):
    """子线程：调后端 /api/graph/invoke"""
    reply_ready = pyqtSignal(str)   # 把 agent 回复发回主线程
    error_occurred = pyqtSignal(str)

    def __init__(self, user_text, parent=None):
        super().__init__(parent)
        self.user_text = user_text

    def run(self):
        try:
            url = "http://localhost:8000/api/graph/invoke"
            resp = requests.get(url, params={"user_input": self.user_text})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    self.reply_ready.emit(data["data"].get("AI_answer", "No response"))
                else:
                    self.error_occurred.emit(data.get("detail", "Unknown error"))
            else:
                self.error_occurred.emit(f"HTTP {resp.status_code}: {resp.text}")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(str(e))
