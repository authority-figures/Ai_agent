from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel


class ChatHistoryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("对话历史")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 聊天历史文本框
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

    def add_message(self, message):
        """添加新消息到聊天历史"""
        # 格式化消息
        formatted_message = f"<b>[{message.get('timestamp', '')}] {message.get('sender', '')}:</b> "
        formatted_message += f"{message.get('content', '')}<br>"

        # 添加到文本框
        self.chat_history.append(formatted_message)

        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )


# 测试入口
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    from datetime import datetime
    # 创建Qt应用实例
    app = QApplication(sys.argv)

    # 实例化要测试的视图
    chat_view = ChatHistoryView()
    chat_view.setWindowTitle("聊天历史视图测试")
    chat_view.resize(600, 400)  # 设置窗口大小

    # 添加测试数据
    test_messages = [
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender": "用户",
            "content": "你好，这个机器人能做什么？"
        },
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender": "系统",
            "content": "我可以执行导航和抓取任务，需要我演示吗？"
        },
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender": "用户",
            "content": "请展示一下导航功能"
        }
    ]

    # 向视图添加测试消息
    for msg in test_messages:
        chat_view.add_message(msg)

    # 显示窗口
    chat_view.show()

    # 启动应用事件循环
    sys.exit(app.exec_())