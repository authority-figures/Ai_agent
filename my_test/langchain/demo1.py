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
langchain.debug = False


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
