from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.messages.tool import ToolCall
from agent_project.agent.llm import chatGPT_llm
from agent_project.agent.tools import load_robot,move_robot_to_target,create_cube,clear_env
  # 假设 ToolCall 是 LangChain 中定义好的类型
from langchain.output_parsers import PydanticOutputParser
from typing import List, Dict
from typing_extensions import Annotated, TypedDict
from langchain.tools import tool  # ✅ 直接使用装饰器
# 定义新的输出模型
# 定义您的输出结构
@tool
class CustomOutput(BaseModel):
    '''    Always use this tool to structure your response to the user.'''
    task:  Annotated[str, ..., "The task you are performing"]
    tool: Annotated[str, ..., "The tool you are using"]


# 定义提示模板
prompt_template = ChatPromptTemplate.from_template(
    """You are an intelligent assistant who must use tools to solve problems。please allways use the CustomOutput tool to structure your response to the user.

{input}
"""
)
# 初始化 ChatOpenAI 模型
llm = chatGPT_llm(
    model_name="gpt-4o-mini", temperature=0
)

simulation_tools = [load_robot,move_robot_to_target,create_cube,clear_env,CustomOutput]

llm_with_tools = llm.bind_tools(simulation_tools)
# llm_with_structure_output = llm_with_tools.with_structured_output(CustomOutput,include_raw=True)
# 组合提示模板和模型，并指定结构化输出
chain = prompt_template | llm_with_tools

# 运行链并获取输出
result = chain.invoke({"input": "Please help me add a robotic arm to the simulation environment at (1,1,0) with the file path F:\ sw\ urdf_files\ minicobo_v1\ urdf\ minicobo_v1. 4.urdf '.",})
print(result)