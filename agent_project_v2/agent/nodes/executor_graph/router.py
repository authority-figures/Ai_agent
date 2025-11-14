
from .state import OverallState
from core.service_locator import ServiceLocator


def router_executor(state:OverallState):
    """根据状态决定下一步"""
    input_text = state.get("input", "").strip().lower()
    tool_calls = state.get("tool_calls", [])

    # # 检查是否要退出
    # if input_text in ["exit", "end", "quit"]:
    #     return "exit"

    # 检查是否有工具调用需要执行
    if tool_calls:
        return "execute_tools"
    else:
        return "exit"

    # 默认返回用户输入节点继续对话
    # return "continue_dialog"


def router_writter(state:OverallState):
    """根据状态决定下一步"""
    input_text = state.get("input", "").strip().lower()
    tool_calls = state.get("tool_calls", [])

    # # 检查是否要退出
    # if input_text in ["exit", "end", "quit"]:
    #     return "exit"

    # 检查是否有工具调用需要执行
    if tool_calls and not state.get("task_finished", False):
        return "execute_tools"
    else:
        return "exit"

    # 默认返回用户输入节点继续对话
    # return "continue_dialog"

async def router_update_node(state:OverallState):
    """根据状态决定下一步"""

    # 检查是否有工具调用需要执行
    if not state.get("task_finished", False):
        return "continue"
    else:
        task = state.get("task", None)
        if task:
            task_id = task.task_id
            print(f"Execution Agent: [Task:{task_id}] complete, exiting.")

            # 在这里发布task_finished_channel 发给interactive agent
            task_repo = ServiceLocator.get("task_repo")
            if task_repo:
                await task_repo.redis.publish("finished_task_channel", task_id)
                print(f"[TaskRepo] published task {task_id} to finished_task_channel")
            else:
                print("TaskRepo not found in ServiceLocator.")

            node_call_counts = state.get("node_call_counts", {})
            for node_name, count in node_call_counts.items():
                print(f"Node '{node_name}' was called {count} times.")

        return "exit"