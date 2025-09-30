import json
import os

from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent_project.agent.llm import chatGPT_llm
# ✅ 引入所有工具
from agent_project.agent.tools import load_robot,create_cube,move_robot_to_target,clear_env,get_robot_end_pos_and_ori
from agent_project.agent.tools import power_on_robot,power_off_robot,enable_robot,disable_robot,joint_move
from agent_project.agent.utils import *
from langchain.prompts import PromptTemplate
from langgraph.graph.message import Messages  # 导入Langchain的Messages类
from agent_project.agent.messages.myMessages import SimpleMessages
import re
from agent_project.agent.utils import truncate_path_to



# 初始化 LLM（使用 OpenAI API 或其他 LLM）
llm = chatGPT_llm(model_name="gpt-4o-mini",temperature=0)
simulation_tools = [load_robot,move_robot_to_target,create_cube,clear_env,get_robot_end_pos_and_ori]
jaka_tools = [power_on_robot,power_off_robot,enable_robot,disable_robot,joint_move]
llm_with_tools = llm.bind_tools(simulation_tools+jaka_tools)

color_printer = ColorPrinter()

current_dir = os.path.dirname(os.path.abspath(__file__))
agent_project_path = truncate_path_to(current_dir, "agent_project")
system_prompt_path = os.path.join(agent_project_path,"agent/prompts/仿真环境执行任务prompts3.txt")
with open(system_prompt_path, 'r', encoding='utf-8') as file:
    # 读取文件的全部内容并存储为字符串
    system_prompt_text = file.read()



# template_text = """
# 请你仔细阅读一下规则，并按照规则要求帮我完成任务。请注意你所执行的任务相当危险，必须严格按照规定执行。你的身份是assistant
# 你需要注意的是：
# 1.在你每次执行任务前，请依据上次执行结果，来判断待解析的任务是否已经全部执行完成；
# 2.若经过你分析后认为待解析的任务没有全部执行完成，则你必须调用一次toolcalls,同时进行文本答复。执行任务前，你要使用{{"准备执行任务":"$(要执行的任务)","Tool":"$(要使用的工具名称，只提供名称)"}}这种模式来进行答复，工具名称需要与toolcalls的内容想对应。只有当你认为解决不了任务时可以不返回toolcalls，并回答任务无法执行；
# 3.若经过你分析后认为待解析的任务全部执行完成，则你不能返回toolcalls，并回答任务执行完成，不用按照之前的模式来进行答复；
# 4.如果你想一次执行多个工具，则你的答复{{"准备执行任务":"$(要执行的任务)","Tool":${{tool_name}} }}需要与执行的工具数量相同，必须将任务拆分成单个工具可以执行的最小任务单元，且tool_name必须与toolcalls中的name相同
#
# 例如：
# '''案例1
# human："请解析任务:请帮我在(0.5, 0.3, 0.2)创建一个红色方块，上次执行结果: []"
# assistant："{{"准备执行任务":"创建一个红色方块于(0.5, 0.3, 0.2)","Tool":"create_cube"}}"
# - toolcalls:[{{'name': 'create_cube', 'args':...}}]
# '''
#
# '''案例2
# human：请解析任务:请帮我在(0.5, 0.3, 0.2)创建一个蓝色方块，上次执行结果: [{{'创建一个蓝色方块于(0.5,0.3,0.2)':{{'Tool': 'create_cube', 'result': {{'status': 'success'}} }} }}
# assistant："任务已完成"
# - toolcalls:[]
# '''
#
# '''案例3 使用多个工具:请注意，一旦你准备同时使用多个工具，你的答复必须包含这些所使用的工具，不要漏掉任何一个toolcalls中使用到的工具。且你必须保证答复中对应的任务中"Tool"的值${{tool_name}}与你所使用工具的名称严格相同
# human：请解析任务:请帮我在(0.5, 0.3, 0.2)创建一个蓝色方块，在(-0.5, 0.3, 0.2)创建一个红色方块，上次执行结果: []
# assistant："{{"准备执行任务":"创建一个蓝色方块于(0.5, 0.3, 0.2)","Tool":"create_cube"}}，{{"准备执行任务":"创建一个红色方块于(-0.5, 0.3, 0.2)","Tool":"create_cube"}}"
# - toolcalls:[{{'name': 'create_cube', 'args':...}},{{'name': 'create_cube', 'args':...}}]
# '''
#
# - 上次执行结果的内容案例为：
# [
#     {{"使用搜索引擎工具进行天气查询": {{"Tool": "搜索引擎工具", "result": "xxx"}}}},
#     {{"使用数据库工具进行数据查询": {{"Tool": "数据库工具", "result": "xxx"}}}}
# ]
#
# 若任务执行完成，则不要生成toolcall，并返回任务结束。
# 请解析任务: {input}。
# 上次执行结果: {previous_action_result}。
#
# """
# 定义正则表达式模式 用于获取LLM回答的字典
pattern = r'\{.*?\}'

# ✅ 让 LLM 只输出 `AgentAction` 指令

template_text = "请解析任务: {input},上次执行结果: {previous_action_result}。"
agent_prompt = PromptTemplate(
    input_variables=["input", "previous_action_result"],
    template=template_text,
)

def generate_agent_action(state):
    """
    统一执行所有的 `AgentAction`
    """
    try:
        print("state",state)
        messages = state.get("messages", SimpleMessages())
        input_text = state.get("input", "")
        action_result = state.get("action_result", [])

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        system_message = SystemMessage(content=system_prompt_text)
        # 将Message.history的内容转化为llm可以invoke的格式化内容
        message_history = [system_message]
        for role, content in messages.history:
            if role == "human":
                message_history.append(HumanMessage(content=content))
            elif role == "assistant":
                message_history.append(AIMessage(content=content))
            elif role == "system":
                message_history.append(SystemMessage(content=content))
        current_task = agent_prompt.format(input=input_text,previous_action_result=action_result)
        message_history.append(HumanMessage(content=current_task))  # 将当前任务添加到消息末尾
        # ----------------------------------------------------------------------------------
        llm_output = llm_with_tools.invoke(message_history)
        messages.add("human", current_task)
        messages.add("assistant", llm_output.content)
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # 解析LLM回答的关于当前要执行的任务
        # matches = re.findall(pattern, llm_output.content)
        # for match in matches:
        #     task_dict = json.loads(match)
        #     if "准备执行任务" in task_dict and "Tool" in task_dict:
        #         action_result.append({task_dict.get("准备执行任务" ):{"Tool":task_dict.get("Tool"),"result":"pending execution"}})
        #
        #
        # print_text = f"LLM says:{llm_output.content}\n当前要执行的任务:{matches}\ntoolcalls:{llm_output.tool_calls}"
        # color_printer.llm_output(print_text)

        # ✅ 解析 `tool_calls`
        tool_calls = llm_output.tool_calls  # tool_calls 是一个 list
        if not tool_calls:
            print_text = f"LLM says:{llm_output.content}"
            color_printer.llm_output(print_text)
            return {"messages": messages,"tool_calls":None,"action_result":action_result}

        current_action_result = []
        for tool_call in tool_calls:
            task = tool_call.get('args').get('description')
            tool_name = tool_call.get('name')
            current_action_result.append({
                "执行任务": task,
                "使用工具": tool_name,
                "执行情况": "pending execution",
                "返回结果": "",

            })
        print_text = f"当前要执行的任务:{current_action_result}\ntoolcalls:{llm_output.tool_calls}"
        color_printer.llm_output(print_text)
        return {"messages": messages,"tool_calls": tool_calls,"action_result":action_result+current_action_result}
    except Exception as e:
        return {"error in generate_agent_action": str(e)}


def agent_node(state):

    # ✅ 返回结果
    return generate_agent_action(state)