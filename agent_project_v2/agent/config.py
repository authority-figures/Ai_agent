import os
from dotenv import load_dotenv,find_dotenv,dotenv_values

# 加载 .env 文件
langsmith_env = dotenv_values(find_dotenv(".env.langsmith"))
openai_api_key = langsmith_env.get("OPENAI_API_KEY")
openai_env = dotenv_values(find_dotenv(".env.openai_yunwu"))


# 读取 API Key 和 Base URL
OPENAI_API_KEY = openai_env.get("API_KEY")
OPENAI_BASE_URL = openai_env.get("BASE_URL")




# 模型名称
GLM3 = "glm-3-turbo"
GLM4 = "glm-4"
DEEPSEEK = "deepseek-v3.2"
DEFAULT_MODEL = "gpt-3.5-turbo"
DOUBAO = "doubao-1-5-thinking-pro-250415"

TEST_MODEL = DEEPSEEK