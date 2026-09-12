#!/usr/bin/env python3
"""LangChain built-in tool example — WikipediaQueryRun.

Shows the full tool-calling flow using a tool LangChain ships out of the box:
the model decides to call it, we execute it, and the result is fed back to
the model for a final answer.

Setup: a local model via Docker Model Runner (see
../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    python 01_builtin_tool.py
"""
import os

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

# Built-in tool — name, description, and parameter schema all come for free.
wikipedia = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=500)
)
print(f"Tool name:        {wikipedia.name}")
print(f"Tool description: {wikipedia.description}")
print(f"Tool args schema: {wikipedia.args}\n")

TOOLS = [wikipedia]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)

messages = [
    SystemMessage(content="You are a helpful assistant. Use the wikipedia tool for factual lookups."),
    HumanMessage(content="Who is Alan Turing? Give me a two-sentence summary."),
]

response = llm_with_tools.invoke(messages)

if response.tool_calls:
    messages.append(response)
    for call in response.tool_calls:
        print(f"Model wants to call: {call['name']}({call['args']})")
        result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    final = llm_with_tools.invoke(messages)
    print(f"\nFinal answer: {final.content}")
else:
    print(f"\nFinal answer: {response.content}")
