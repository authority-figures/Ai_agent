from langgraph.graph import Graph, END, StateGraph
from typing import TypedDict

# 定义状态：包含计数器和终止标记
class State(TypedDict):
    count: int
    should_stop: bool

# 节点1：执行循环任务（计数器+1）
def task_node(state: State) -> State:
    state["count"] += 1
    print(f"执行第 {state['count']} 次循环")
    # 执行5次后标记终止
    state["should_stop"] = state["count"] >= 5
    return state

# 节点2：决策节点（判断是否继续循环）
def decision_node(state: State) -> str:
    # 若满足终止条件，返回END；否则回到task_node继续循环
    if state["should_stop"]:
        return END
    else:
        return "task"

# 构建循环图
graph = StateGraph(State)
graph.add_node("task", task_node)
graph.add_node("decision", decision_node)

# 定义循环逻辑：task → decision → task（形成环）
# graph.add_edge("task", "decision")
# graph.add_edge("decision", "task")  # 循环边
graph.add_conditional_edges("task",decision_node,{"task": "task",END: END,},)

# 设置入口点
graph.set_entry_point("task")

# 编译并运行
compiled_graph = graph.compile()
compiled_graph.invoke({"count": 0, "should_stop": False})