from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="docker.io/llama3.2:1B-Q8_0", 
    base_url="http://localhost:12434/engines/llama.cpp/v1", 
    api_key="not-needed", 
    temperature=0)

response = llm.invoke([
    HumanMessage(content="What is the capital of France?")])
print(response.content)