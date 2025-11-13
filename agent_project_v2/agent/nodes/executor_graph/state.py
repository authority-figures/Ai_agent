from typing import TypedDict,Annotated,Optional,List,Dict
from langgraph.graph import StateGraph, START, END
import operator
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from core.task import Task


# 增量更新操作
def increment(node_call_counts: Dict[str, int], node: str, increment_by: int = 1):
    node_call_counts[node] = node_call_counts.get(node, 0) + increment_by
    return node_call_counts

# ✅ 1. 定义 `State`，LangGraph 任务的状态信息
class AgentState(TypedDict):
    input: str
    messages: list  # 使用Langchain的Messages类    agent_action: AgentAction | None
    action_result: Annotated[list, lambda x, y: x + y]
    tool_calls: Optional[List]   # 存储工具调用


class OverallState(TypedDict):
    input_type: str
    input: str
    task_id: str
    task: Optional[Task]
    ifsuccess: bool
    task_finished: bool
    AI_answer: str
    messages: Annotated[List[BaseMessage], add_messages]
    action_result: list  # 存储工具调用结果
    tool_calls: list # 存储工具调用
    task_pushed: bool
    exec_tool_messages: Annotated[List[BaseMessage], add_messages]
    write_tool_messages: Annotated[List[BaseMessage], add_messages]
    node_call_counts: Optional[Dict[str, int]]  # 记录各节点调用次数