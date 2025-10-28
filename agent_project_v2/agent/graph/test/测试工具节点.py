from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph.message import add_messages
from agent_project_v2.agent.llm import chatGPT_llm

# 定义工具
@tool
def get_weather(location: str) -> str:
    """获取指定地点的天气"""
    if location.lower() in ["sf", "san francisco"]:
        return "60 度，多雾"
    return "90 度，晴天"




# 定义状态
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


def chatbot_node(state: State) -> State:
    """自定义的聊天节点，手动调用 llm.invoke"""
    messages = state["messages"]

    # 调用 LLM
    response = llm.invoke(messages)

    # # 打印调试信息（可选）
    # print(f"[Chatbot Node] Input: {messages[-1].content}")
    # print(f"[Chatbot Node] Output: {response.content}")

    # 返回新的状态，LangGraph 会自动合并（append）
    return {"messages": [response]}


# 初始化 LLM 和工具
# llm = chatGPT_llm(model="gpt-4o-mini").bind_tools([get_weather])
llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
llm = llm.bind_tools([get_weather])
# 创建 StateGraph
workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot_node)
workflow.add_node("tools", ToolNode(tools=[get_weather]))
workflow.add_edge(START, "chatbot")
workflow.add_conditional_edges("chatbot", tools_condition, {"tools": "tools", END: END})
workflow.add_edge("tools", "chatbot")

# 编译和运行
graph = workflow.compile()
result = graph.invoke({"messages": [HumanMessage(content="旧金山的天气如何？")]})
print(result["messages"][-1].content)  # 例如：旧金山的天气是 60 度，多雾
