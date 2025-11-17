# qt_log_handler.py
import logging
from PyQt5.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)  # 用信号把日志发给主线程

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        logging.Handler.__init__(self)

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        # 通过信号发出去，Qt 会自动做线程间的调度（QueuedConnection）
        self.log_signal.emit(msg)
