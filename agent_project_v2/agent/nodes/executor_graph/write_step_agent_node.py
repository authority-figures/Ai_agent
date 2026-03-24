
from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent.llm import chatGPT_llm

from agent.nodes.executor_graph.state import OverallState
from agent.tools.exec_graph_tools import using_tools
import time
from agent.utils import ColorPrinter


llm = chatGPT_llm(model_name="gpt-4o",temperature=0)
llm_with_tools = llm.bind_tools(using_tools)
# system_prompt = ("你是一个AI助理,负责依据task中step的执行情况来填写对应的字段,请注意，你需要将上个执行的结果的详细数据也一并写入log中.你可以使用工具来提交修改.每次只填写一个任务，即在所有的step当中的第一个状态为pending的任务,不要修改状态为finished的任务\n"
#                  "当得知任务执行完毕时（上一个代理回答任务执行完毕或所有的step状态均为finished），你需要回复任务执行完毕,且不要调用工具\n")

system_prompt = f"""
你是一个AI助理,负责依据task中step的执行情况来填写对应的字段,请注意，你需要将上个执行的结果的详细数据也一并写入log中(包括执行过程使用的工具名称以及输入参数).
你可以使用工具来提交修改.每次只填写一个任务，即在所有的step当中的第一个状态为pending的任务,不要修改状态为finished的任务
当你发现上一个代理执行的是上次失败任务的重新尝试时，你需要在原来的step中追加填写log,而不是新建一个step。若发现尝试成功，则将该step状态修改为finished。
当得知任务执行完毕时（上一个代理回答任务执行完毕或所有的step状态均为finished），你需要回复任务执行完毕,且不要调用工具

"""

class AgentNode:
    def __init__(self,config):
        self.config = config

    async def __call__(self, state: OverallState):
        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[write_step_agent_node] |{time_}|进入write_step_agent_node节点")

        if state.get("task_finished", False):   # 快速结束
            time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            ColorPrinter.debug_normal(f"[write_step_agent_node] |{time_}|离开write_step_agent_node节点 快速结束")
            return {"messages": state.get("messages", []), "tool_calls": None, "task_finished": True,}

        messages = state.get("messages", [])
        task = state.get("task", None)
        if not task:
            print("没有获取到任务，无法执行步骤。")
            return {"messages": messages, "tool_calls": None, }

        tool_calls = state.get("tool_calls", [])
        print("DEBUG: write_step_agent_node获取到的tool_calls内容：", tool_calls)

        prompt = f"""task的内容如下: \n{task}\n。
                上一个代理的任务执行情况如下：\n{messages[-1].content}\n 
                上一个代理使用的工具调用情况如下：\n{tool_calls}\n
                """
        input = HumanMessage(content=prompt)
        system_message = SystemMessage(content=system_prompt)
        message_history = [system_message] + [input]

        llm_output = await llm_with_tools.ainvoke(message_history)

        messages.append(llm_output)

        tool_calls, current_action_result = self.toolcall_parsing(llm_output)

        node_call_counts = state.get("node_call_counts", {})
        node_call_counts["write_step_agent"] = node_call_counts.get("write_step_agent", 0) + 1

        time_ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ColorPrinter.debug_normal(f"[write_step_agent_node] |{time_}|离开write_step_agent_node节点")

        if not tool_calls or state.get("task_finished", False):
            return {"messages": messages, "tool_calls": None, "node_call_counts": node_call_counts,
                    "task_finished": True}
        else:
            # return {"messages": messages}  # 返回更新后的消息历史
            return {"messages": messages, "tool_calls": tool_calls,"node_call_counts": node_call_counts, "task_finished": False,

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






