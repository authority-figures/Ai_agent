from typing import TypedDict,Annotated,Optional,List
from langgraph.graph import StateGraph, START, END


# ✅ 1. 定义 `State`，LangGraph 任务的状态信息
class AgentState(TypedDict):
    input: str
    messages: list  # 使用Langchain的Messages类    agent_action: AgentAction | None
    action_result: Annotated[list, lambda x, y: x + y]
    tool_calls: Optional[List]   # 存储工具调用


class OverallState(TypedDict):
    agent_state: AgentState
    user_input: str