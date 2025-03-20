from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

search = TavilySearchResults(max_results=1)

loader = WebBaseLoader("https://zh.wikipedia.org/wiki/%E7%8C%AB")
docs = loader.load()
doucments = RecursiveCharacterTextSplitter(
    chunk_size=1000,chunk_overlap=200
).split_documents(docs)

vector = FAISS.from_documents(doucments,OpenAIEmbeddings())
retriever = vector.as_retriever()
