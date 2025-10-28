'''
用于处理用户输入的中断命令的节点模块。
'''

# nodes/command_handler.py
from command_queue import command_manager, CommandType
from state import AgentState as RobotArmState

def command_handler_node(state: RobotArmState, config: dict) -> dict:
    """非阻塞命令处理节点"""
    thread_id = config["configurable"]["thread_id"]

    # 非阻塞获取命令
    command = command_manager.get_command_for_thread(thread_id, block=False)

    if command is None:
        # 没有新命令，保持当前状态
        return {}

    # 处理命令
    result = {}
    if command.command_type == CommandType.PAUSE:
        result.update({"is_paused": True, "pending_command": None})
        print(f"Thread {thread_id}: 已暂停")

    elif command.command_type == CommandType.RESUME:
        result.update({"is_paused": False, "pending_command": None})
        print(f"Thread {thread_id}: 已恢复")

    elif command.command_type == CommandType.RESET:
        result.update({
            "is_paused": False,
            "should_reset": True,
            "plan": [],
            "current_step_index": 0,
            "user_input": command.data.get("new_mission", ""),
            "pending_command": None
        })
        print(f"Thread {thread_id}: 重置任务")

    return result