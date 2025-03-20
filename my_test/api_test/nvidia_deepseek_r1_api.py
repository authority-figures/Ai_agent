from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
import os

# 加载 .env.nvidia 文件
_ = load_dotenv(find_dotenv(".env.openai_taobao"))

# 获取 API_KEY 和 BASE_URL
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")



client = OpenAI(
  base_url = base_url,
  api_key = api_key
)

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[{"role":"user","content":"Which number is larger, 9.11 or 9.8?"}],
  temperature=0.6,
  top_p=0.7,
  max_tokens=4096,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

