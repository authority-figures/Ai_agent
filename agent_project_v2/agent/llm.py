# from langchain.chat_models import ChatOpenAI
import sys,os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
from langchain_openai import ChatOpenAI
import httpx
from config import OPENAI_API_KEY, OPENAI_BASE_URL, DEFAULT_MODEL


CLASH_HTTP_PROXY = "http://127.0.0.1:7890"   # Clash HTTP 代理

# 统一管理 LLM 实例
def chatGPT_llm(model_name=DEFAULT_MODEL, temperature=0.2):
    """
    创建 LLM 实例
    :param model_name: 指定 LLM 模型
    :param temperature: LLM 生成文本的温度（影响随机性）
    :return: Langchain ChatOpenAI 实例
    """

    sync_client = httpx.Client(
        proxy=CLASH_HTTP_PROXY,
        timeout=30.0,
    )
    async_client = httpx.AsyncClient(
        proxy=CLASH_HTTP_PROXY,
        timeout=30.0,
    )


    return ChatOpenAI(
        temperature=temperature,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=model_name,
        # http_client=sync_client,  # 同步 invoke() 用这个
        # http_async_client=async_client,  # ainvoke()/astream() 用这个
    )


if __name__ == '__main__':
    llm = chatGPT_llm(model_name="deepseek-v3-0324")
    print(llm.invoke("hello").content)