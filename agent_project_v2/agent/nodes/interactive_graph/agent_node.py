from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import Graph, END, StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, List
from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent_project_v2.agent.llm import chatGPT_llm

from agent.nodes.interactive_graph.state import OverallState
from agent.tools.interactive_graph_tools import using_tools
from agent.nodes.node_publisher import send_state
import time
from agent.utils import ColorPrinter
from agent_project_v2.agent.config import *


llm = chatGPT_llm(model_name=TEST_MODEL,temperature=0)
llm_with_tools = llm.bind_tools(using_tools)
system_prompt = f"""
你是一个AI助理,请回答用户的问题,必要时可以使用工具
当需要发布任务时，你每次只能发送一次任务
"""

class AgentNode:
    def __init__(self,config):
        self.config = config

    async def __call__(self, state: OverallState):
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[interactive_agent_node] |{time_}|进入interactive_agent_node节点",color="green")
        messages = state.get("messages", [])
        action_result = state.get("action_result", [])
        system_message = SystemMessage(content=system_prompt)
        message_history = [system_message] + messages

        llm_output = await llm_with_tools.ainvoke(message_history)


        messages.append(llm_output)

        tool_calls, current_action_result = self.toolcall_parsing(llm_output)

        send_state("agent_node",{"status":"running","content":f"llm_output:{llm_output.content}\ntool_calls:{tool_calls}"})

        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[interactive_agent_node] |{time_}|离开interactive_agent_node节点",color="green")

        if not tool_calls:
            return { "messages": messages,"tool_calls": None, "action_result": state.get("action_result", []),"AI_answer": llm_output.content}
        else:
            # return {"messages": messages}  # 返回更新后的消息历史
            return {"messages": messages, "action_result": action_result + current_action_result,"tool_calls":tool_calls

                    }
        pass

    def toolcall_parsing(self,llm_output):
        # 解析 llm output toolcalls
        current_action = []
        tool_calls = llm_output.tool_calls  # tool_calls 是一个 list
        if not tool_calls:
            return [], []
        else:
            for tool_call in tool_calls:
                task = tool_call.get('args').get('description')
                tool_name = tool_call.get('name')
                current_action.append({
                    "task_name": task,
                    "tool_name": tool_name,
                    "status": "pending execution",
                    "result": "",
                })
            return tool_calls,current_action






