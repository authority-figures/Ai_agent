from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain import hub
from langchain.agents import create_tool_calling_agent
from langgraph.prebuilt.tool_executor import ToolExecutor
# from langchain_openai import OpenAI
# from langchain.chat_models import ChatOpenAI
from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv,find_dotenv,dotenv_values
import os


from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import AgentExecutor,create_openai_tools_agent



openai_env = dotenv_values(find_dotenv(".env.openai_taobao"))
os.environ["TAVILY_API_KEY"] = "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"
os.environ["OPENAI_API_KEY"] = openai_env.get("API_KEY")
os.environ["OPENAI_BASE_URL"] = openai_env.get("BASE_URL")
search = TavilySearchResults( max_results=1)


loader = WebBaseLoader("https://zh.wikipedia.org/wiki/%E7%8C%AB")
docs = loader.load()
doucments = RecursiveCharacterTextSplitter(
    chunk_size=1000,chunk_overlap=200
).split_documents(docs)

vector = FAISS.from_documents(doucments,OpenAIEmbeddings())
retriever = vector.as_retriever()
retriever_tool = create_retriever_tool(
    retriever,
    "wiki_search",
    "搜索维基百科"
)



# 获取 API_KEY 和 BASE_URL
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model = ChatOpenAI(
    temperature=0.2,
    api_key=api_key,
    base_url=base_url,
    model="gpt-3.5-turbo"
)
tools = [retriever_tool]

model.bind_tools(tools)
prompt = hub.pull("hwchase17/openai-functions-agent")
agent = create_openai_tools_agent(model, tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

response = agent_with_chat_history.invoke(
    {"input": "你好，我的名字叫王灿"},
    config={"configurable": {"session_id": "123"}},
)

print(response)


response = agent_with_chat_history.invoke(
    {"input": "我叫什么名字？"},
    config={"configurable": {"session_id": "123"}},
)
print(response)
print(store)