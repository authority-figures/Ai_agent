from PyQt5.QtCore import QObject, pyqtSignal
import asyncio
from typing import Any, Dict


class AsyncRunner(QObject):
    """
    帮你在其他线程 / 事件循环里跑协程，
    跑完后通过 finished 信号把结果丢回到 Qt 主线程。
    """
    finished = pyqtSignal(object)  # 也可以是 dict，这里用 object 更灵活

    def run(self, loop: asyncio.AbstractEventLoop, coro):
        """
        loop: 你的 env_loop
        coro: 要执行的协程对象，比如 synchronize_digital_twin_state()
        """
        future = asyncio.run_coroutine_threadsafe(coro, loop)

        def _done(fut):
            try:
                result = fut.result()
            except Exception as e:
                # 出错也传回去，避免静默失败
                result = {"status": "error", "message": str(e)}
            # 注意：可以在任何线程 emit，Qt 会自动用 QueuedConnection
            self.finished.emit(result)

        future.add_done_callback(_done)