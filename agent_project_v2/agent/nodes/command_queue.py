'''
用于为command——handler——node提供线程安全的命令队列管理功能。
'''

import queue
import threading
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


class CommandType(Enum):
    PAUSE = "pause"
    RESUME = "resume"
    RESET = "reset"
    STOP = "stop"


@dataclass
class Command:
    command_type: CommandType
    data: Dict[str, Any]
    timestamp: datetime
    thread_id: str  # 关联特定的工作流实例


class CommandQueueManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_queue()
            return cls._instance

    def _init_queue(self):
        """初始化线程安全队列"""
        self.command_queue = queue.Queue()
        self.thread_queues: Dict[str, queue.Queue] = {}  # 按thread_id隔离的队列
        self.thread_locks: Dict[str, threading.Lock] = {}

    def send_command(self, command: Command):
        """发送命令到全局队列"""
        self.command_queue.put(command)

    def get_command_for_thread(self, thread_id: str, block: bool = False, timeout: float = 0.1) -> Optional[Command]:
        """获取特定线程的命令（非阻塞）"""
        try:
            # 检查全局队列中是否有该thread_id的命令
            if not self.command_queue.empty():
                # 临时保存非目标thread_id的命令
                temp_commands = []
                found_command = None

                while not self.command_queue.empty():
                    cmd = self.command_queue.get_nowait()
                    if cmd.thread_id == thread_id:
                        found_command = cmd
                        break
                    else:
                        temp_commands.append(cmd)

                # 将其他命令放回队列
                for cmd in temp_commands:
                    self.command_queue.put(cmd)

                return found_command
        except queue.Empty:
            pass

        return None


# 全局单例实例
command_manager = CommandQueueManager()