from openai import OpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv,find_dotenv
import os


# 加载 .env.nvidia 文件
_ = load_dotenv(find_dotenv(".env.nvidia"))

# 获取 API_KEY 和 BASE_URL
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")



client = OpenAI(
  base_url = base_url,
  api_key = api_key
)

prompt_template = PromptTemplate(
    input_variables=["num1", "num2", "language"],
    template="Which number is larger, {num1} or {num2}?,answer in {language}"
)

# 提供具体的输入值
num1 = 10
num2 = 20
language = "Chinese"

# 格式化提示词
formatted_prompt = prompt_template.format(num1=num1, num2=num2, language=language)


completion = client.chat.completions.create(
  model="deepseek-ai/deepseek-r1",
  messages=[{"role":"user","content":formatted_prompt}],
  temperature=0.6,
  top_p=0.7,
  max_tokens=4096,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")
