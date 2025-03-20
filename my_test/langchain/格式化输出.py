from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from dotenv import load_dotenv,find_dotenv
import os


# 加载 .env.nvidia 文件
_ = load_dotenv(find_dotenv(".env.nvidia"))
# 获取 API_KEY 和 BASE_URL
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")


class MyOutputParser(BaseOutputParser):
    def parse(self, output: str) -> dict:
        # 查找 <think> 标签的起始和结束位置
        start_index = output.find("<think>")
        end_index = output.find("</think>")

        if start_index != -1 and end_index != -1:
            # 提取 <think> 标签内的思考内容
            think_content = output[start_index + len("<think>"):end_index].strip()
            # 提取 <think> 标签之后的回答内容
            answer_content = output[end_index + len("</think>"):].strip()
            return {
                "think": think_content,
                "answer": answer_content
            }
        else:
            return {
                "think": "",
                "answer": output.strip()
            }



# 调用模型生成流式响应
client = OpenAI(
  base_url = base_url,
  api_key = api_key
)
completion = client.chat.completions.create(
    model="deepseek-ai/deepseek-r1",
    messages=[{"role": "user", "content": "Which number is larger, 9.11 or 9.8?"}],
    temperature=0.6,
    top_p=0.7,
    max_tokens=4096,
    stream=True
)

# 累积流式输出
full_output = ""
for chunk in completion:
    if chunk.choices[0].delta.content is not None:
        full_output += chunk.choices[0].delta.content
        print(chunk.choices[0].delta.content, end="")
# 创建输出解析器实例
parser = MyOutputParser()
# 解析输出
parsed_result = parser.parse(full_output)

# 打印解析结果
print("思考内容:")
print(parsed_result["think"])
print("\n回答内容:")
print(parsed_result["answer"])