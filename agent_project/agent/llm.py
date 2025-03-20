# from langchain.chat_models import ChatOpenAI
import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, DEFAULT_MODEL


# 统一管理 LLM 实例
def chatGPT_llm(model_name=DEFAULT_MODEL, temperature=0.2):
    """
    创建 LLM 实例
    :param model_name: 指定 LLM 模型
    :param temperature: LLM 生成文本的温度（影响随机性）
    :return: Langchain ChatOpenAI 实例
    """



    return ChatOpenAI(
        temperature=temperature,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=model_name,

    )
