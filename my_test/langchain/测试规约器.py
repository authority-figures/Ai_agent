from typing import Annotated, TypedDict
from operator import add

class OverallState(TypedDict):
    task_id: str
    status: str
    i: Annotated[int, add]  # 记录某个整数值并进行增量更新
    node_call_counts: Annotated[dict[str, int], add]  # 记录节点调用次数并进行增量更新

# 初始状态
state = {"task_id": "t-123", "status": "running", "node_call_counts": {"node1": 1},"i":1}

# 更新状态
state.update({"node_call_counts": {"node1": 2},"i":state.get("i")+1})  # 将 node1 的调用次数增加 1
print(state)
state.update({"node_call_counts": {"node2": 1}})  # 新增 node2 的调用次数

# 打印更新后的状态
print(state)
