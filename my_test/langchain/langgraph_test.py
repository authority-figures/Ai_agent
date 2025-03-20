# ！/usr/bin env python3
# -*- coding: utf-8 -*-
# author: yangyunlong time:2024/2/28
import datetime
import operator
from typing import Optional
from typing import TypedDict, Annotated, Union, Optional,Type,List
from pprint import pprint  # 导入 pprint 模块
import requests
from langchain import hub
from langchain.agents import create_openai_tools_agent,AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain_core.agents import AgentAction
from langchain_core.agents import AgentFinish
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_executor import ToolExecutor
# from langchain_openai import OpenAI
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv,find_dotenv,dotenv_values
import os
# from langchain.callbacks import BaseCallbackHandler
import langchain
langchain.debug = True


_ = load_dotenv(find_dotenv(".env.openai_taobao"))

# 获取 API_KEY 和 BASE_URL
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
glm3 = "glm-3-turbo"
glm4 = "glm-4"
deepseek = "deepseek-ai/deepseek-r1"
# chatgpt = ChatZhipuAI(
#     temperature=0.2,
#     api_key=api_key,
#     model=glm4
# )
chatgpt = ChatOpenAI(
    temperature=0.2,
    api_key=api_key,
    base_url=base_url,
    model="gpt-3.5-turbo"
)


langsmith_env = dotenv_values("F:\python\Ai_agent\.env.langsmith")
# os.environ["LANGSMITH_TRACING"] = "true"
# os.environ["LANGSMITH_ENDPOINT"] = langsmith_env.get("LANGSMITH_ENDPOINT")
# os.environ["LANGSMITH_API_KEY"] = langsmith_env.get("LANGSMITH_API_KEY")
# os.environ["LANGSMITH_PROJECT"] = langsmith_env.get("LANGSMITH_PROJECT")


class Tagging(BaseModel):
    """分析句子的情感极性，并输出句子对应的语言"""
    sentiment: str = Field(description="sentiment of text, should be `pos`, `neg`, or `neutral`")
    language: str = Field(description="language of text (should be ISO 639-1 code)")


class Overview(BaseModel):
    """Overview of a section of text."""
    summary: str = Field(description="Provide a concise summary of the content.")
    language: str = Field(description="Provide the language that the content is written in.")
    keywords: str = Field(description="Provide keywords related to the content.")


@tool("tagging", args_schema=Tagging)
def tagging(s1: str, s2: str):
    """分析句子的情感极性，并输出句子对应的语言"""
    return "The sentiment is {a}, the language is {b}".format(a=s1, b=s2)


@tool("overview", args_schema=Overview)
def overview(summary: str, language: str, keywords: str):
    """Overview of a section of text."""
    return "Summary: {a}\nLanguage: {b}\nKeywords: {c}".format(a=summary, b=language, c=keywords)


@tool
def get_current_temperature(latitude: float, longitude: float):
    """Fetch current temperature for given coordinates."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Parameters for the request
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m',
        'forecast_days': 1,
    }

    # Make the request
    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        results = response.json()
    else:
        raise Exception(f"API Request failed with status code: {response.status_code}")

    current_utc_time = datetime.datetime.utcnow()
    time_list = [datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00')) for time_str in
                 results['hourly']['time']]
    temperature_list = results['hourly']['temperature_2m']

    closest_time_index = min(range(len(time_list)), key=lambda i: abs(time_list[i] - current_utc_time))
    current_temperature = temperature_list[closest_time_index]

    return f'The current temperature is {current_temperature}°C'





@tool
def get_current_time(timezone: Optional[str] = None):
    """Fetch current date for today."""
    """
    获取今天的具体日期与时间。

    参数:
        timezone (str, optional): 时区名称，例如 "Asia/Shanghai"。默认为 None（UTC 时间）。

    返回:
        str: 当前时间的字符串表示
    """
    if timezone:
        try:
            import pytz  # 需要安装 pytz 库
            tz = pytz.timezone(timezone)
            current_time = datetime.datetime.now(tz)
        except ImportError:
            return "需要安装 pytz 库以支持时区功能。请运行 `pip install pytz`。"
        except pytz.exceptions.UnknownTimeZoneError:
            return f"未知时区: {timezone}"
    else:
        current_time = datetime.datetime.utcnow()

    return f"当前时间是: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"

@tool
def get_temperature_at_time(latitude: float, longitude: float, date: str, time: str = "12:00"):
    """
    查询指定日期和时间的温度。

    参数:
        latitude (float): 纬度
        longitude (float): 经度
        date (str): 日期，格式为 "YYYY-MM-DD"
        time (str): 时间，格式为 "HH:MM"，默认为 "12:00"（中午）

    返回:
        str: 指定日期和时间的温度
    """
    # 将日期和时间合并为 ISO 格式
    datetime_str = f"{date}T{time}"
    try:
        target_time = datetime.datetime.fromisoformat(datetime_str)
    except ValueError:
        return "日期或时间格式错误，请使用 'YYYY-MM-DD' 和 'HH:MM' 格式。"

    # 调用 Open-Meteo API
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m',
        'start_date': date,
        'end_date': date,
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        return f"API 请求失败，状态码: {response.status_code}"

    results = response.json()

    # 解析时间和温度数据
    time_list = [datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00')) for time_str in
                 results['hourly']['time']]
    temperature_list = results['hourly']['temperature_2m']

    # 找到最接近目标时间的温度
    closest_time_index = min(range(len(time_list)), key=lambda i: abs(time_list[i] - target_time))
    closest_temperature = temperature_list[closest_time_index]

    return f"{date} {time} 的温度是 {closest_temperature}°C"


@tool
def subtract(a: float, b: float) -> float:
    """Subtracts b from a and returns the result."""
    return a - b




tools = [get_temperature_at_time,get_current_time,subtract]
# Get the prompt to use - you can modify this!
# prompt = hub.pull("hwchase17/openai-tools-agent")
# # 如果你想修改第一个消息，可以创建一个新的消息并替换
# prompt.messages[0] = prompt.messages[0].copy(update={"content": "You are a helpful assistant. 当你需要今天的日期时, 请你使用 "
#                                                                 "`get_current_time` 工具,当你需要查询某天的温度，你可以使用 `get_temperature_at_time`."})

# 构建模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位非常有用的助理.而且善于使用工具解决问题。 当你需要知道今天的日期时，请使用工具来获取到今天的日期。当你需要知道某一天的气温时，使用`get_temperature_at_time`.注意使用该工具时，一次只能获取一天的气温,当你需要知道两个不同日期的气温时，需要分别使用两次该工具"),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])



print(prompt)

# class ThoughtCallbackHandler(BaseCallbackHandler):
#     def on_llm_start(self, serialized, prompts, **kwargs):
#         print(f"Model Input: {prompts}")
#
#     def on_llm_end(self, response, **kwargs):
#         print(f"Model Output: {response.generations[0][0].text}")

# Construct the OpenAI Functions agent
agent_runnable = create_openai_tools_agent(chatgpt, tools, prompt,)
# 包装到 AgentExecutor 并设置 verbose=True
agent_executor = AgentExecutor(agent=agent_runnable, tools=tools, verbose=True,return_intermediate_steps=True)

class AgentState(TypedDict):
    # The input string
    input: str
    # The list of previous messages in the conversation
    chat_history: list[BaseMessage]
    # The outcome of a given call to the agent
    # Needs `None` as a valid type, since this is what this will start as
    agent_outcome: Union[AgentAction, AgentFinish, None]
    # List of actions and corresponding observations
    # Here we annotate this with `operator.add` to indicate that operations to
    # this state should be ADDED to the existing values (not overwrite it)
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    reasoning_log: Annotated[list[str], operator.add]  # ✅ 让 `reasoning_log` 进行累积

# This a helper class we have that is useful for running tools
# It takes in an agent action and calls that tool and returns the result

tool_executor = ToolExecutor(tools)

# Define the agent
def run_agent(data):


    agent_response  = agent_executor.invoke({
            "input": data["input"],

            "chat_history": data["chat_history"],
            # "agent_outcome":data.get("agent_outcome",[]),
            "reasoning_log": data.get("reasoning_log", []),  # ✅ 传递 `reasoning_log`
        },)
    # ✅ 记录代理的思维链
    reasoning_log = data.get("reasoning_log", [])  # 取已有的记录
    # 提取正确的返回值
    intermediate_steps = agent_response.get("intermediate_steps", [])

    # 获取最后一个AgentAction
    agent_outcome = intermediate_steps[-1][0] if intermediate_steps else None
    print("in run_agent,agent_outcome:{}".format(agent_outcome))
    # ✅ 只有当代理生成 `AgentAction` 时，才存入日志
    if isinstance(agent_outcome, AgentAction):
        reasoning_log.append(agent_outcome.log)  # 存储思维链
    return {"agent_outcome": agent_outcome, "reasoning_log": reasoning_log}
    # return {"agent_outcome": agent_outcome}


# Define the function to execute tools
def execute_tools(data):
    # Get the most recent agent_outcome - this is the key added in the `agent` above
    agent_action = data["agent_outcome"]
    print("agent action:{}".format(agent_action))
    # 类型安全校验
    if not isinstance(agent_action, AgentAction):
        raise ValueError(f"期望AgentAction，实际得到{type(agent_action)}")

    # 执行工具
    output = tool_executor.invoke(agent_action)  # ✅ 直接传递AgentAction对象


    return {
        "intermediate_steps": [(agent_action, str(output))],
        "reasoning_log": data.get("reasoning_log", [])
    }


# Define logic that will be used to determine which conditional edge to go down
def should_continue(data):
    # If the agent outcome is an AgentFinish, then we return `exit` string
    # This will be used when setting up the graph to define the flow
    if isinstance(data["agent_outcome"], AgentFinish):
        return "end"
    # Otherwise, an AgentAction is returned
    # Here we return `continue` string
    # This will be used when setting up the graph to define the flow
    else:
        return "continue"


# Define a new graph
workflow = StateGraph(AgentState)

# Define the two nodes we will cycle between
workflow.add_node("agent", run_agent)
workflow.add_node("action", execute_tools)

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
    # Finally we pass in a mapping.
    # The keys are strings, and the values are other nodes.
    # END is a special node marking that the graph should finish.
    # What will happen is we will call `should_continue`, and then the output of that
    # will be matched against the keys in this mapping.
    # Based on which one it matches, that node will then be called.
    {
        # If `tools`, then we call the tool node.
        "continue": "action",
        # Otherwise we finish.
        "end": END,
    },
)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge("action", "agent")

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile()

inputs = {"input": "华中科技大学今天和昨天的气温差是多少？", "chat_history": []}
result = app.invoke(inputs)
print(result["agent_outcome"].messages[0].content)


# 打印完整的 result 内容
print("完整 result 内容：")
pprint(result)