from typing import TypedDict,Annotated,Optional,List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ✅ 1. 定义 `State`，LangGraph 任务的状态信息
class AgentState(TypedDict):
    input: str
    messages: list  # 使用Langchain的Messages类    agent_action: AgentAction | None
    action_result: Annotated[list, lambda x, y: x + y]
    tool_calls: Optional[List]   # 存储工具调用


class OverallState(TypedDict):
    input_type: str
    input: str
    AI_answer: str
    messages: Annotated[List[BaseMessage], add_messages]
    action_result: list  # 存储工具调用结果
    tool_calls: list # 存储工具调用