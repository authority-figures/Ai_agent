
from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent.llm import chatGPT_llm

from agent.nodes.executor_graph.state import OverallState
from agent.tools.simulation_tools import using_tools




llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
llm_with_tools = llm.bind_tools(using_tools)
system_prompt = "你是一个AI助理,负责依据task中制定的plan来执行对应的step，你可以使用工具来执行对应的步骤.若没有可用的工具完成任务，则回复任务无法完成，无合适工具。若任务所需参数不足，则回复参数不足\n"

class AgentNode:
    def __init__(self,config):
        self.config = config

    def __call__(self, state: OverallState):
        messages = state.get("messages", [])
        task = state.get("task", None)
        if not task:
            print("没有获取到任务，无法执行步骤。")
            return {"messages": messages, "tool_calls": None,}

        prompt = f"请你依据任务表的plan内容以及execution字段的执行情况，开始执行每个step: \n{task}\n"
        input = HumanMessage(content=prompt)
        system_message = SystemMessage(content=system_prompt)
        message_history = [system_message] + [input]

        llm_output = llm_with_tools.invoke(message_history)


        messages.append(llm_output)

        tool_calls, current_action_result = self.toolcall_parsing(llm_output)


        if not tool_calls:
            return { "messages": messages,"tool_calls": None,}
        else:
            # return {"messages": messages}  # 返回更新后的消息历史
            return {"messages": messages, "tool_calls":tool_calls

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






