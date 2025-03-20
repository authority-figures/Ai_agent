from langchain_openai import ChatOpenAI
from dotenv import load_dotenv,find_dotenv,dotenv_values
import os,sys

langsmith_env = dotenv_values("F:\python\Ai_agent\.env.langsmith")


openai_api_key = langsmith_env.get("OPENAI_API_KEY")



os.environ["OPENAI_API_KEY"] = langsmith_env.get("OPENAI_API_KEY")
os.environ["BASE_URL"] = "https://api.nuwaapi.com/v1"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = langsmith_env.get("LANGSMITH_ENDPOINT")
os.environ["LANGSMITH_API_KEY"] = langsmith_env.get("LANGSMITH_API_KEY")
os.environ["LANGSMITH_PROJECT"] = langsmith_env.get("LANGSMITH_PROJECT")


llm = ChatOpenAI(
    base_url = "https://api.nuwaapi.com/v1",
    api_key = langsmith_env.get("OPENAI_API_KEY")
)
llm.invoke("Hello, world!")