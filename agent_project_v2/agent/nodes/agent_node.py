import json
import os

from langchain.schema import AgentAction,HumanMessage,SystemMessage,AIMessage
from agent_project_v2.agent.llm import chatGPT_llm
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





