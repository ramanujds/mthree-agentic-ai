#!/usr/bin/env python3
"""LangChain custom tool example — the @tool decorator.

Wraps a plain Python function as a tool: LangChain derives the tool's name,
description, and parameter schema from the function name, docstring, and
type hints (compare wikipedia.args in 01_builtin_tool.py — same shape, but
here you wrote the function instead of importing it).

Setup: a local model via Docker Model Runner (see
../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    python 02_custom_tool.py
"""
import os

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")


@tool
def get_stock_price(ticker: str) -> str:
    """Look up the current stock price for a given ticker symbol."""
    fake_prices = {"AAPL": 227.5, "GOOG": 172.3, "MSFT": 418.9}
    price = fake_prices.get(ticker.upper())
    if price is None:
        return f"No price data for '{ticker}'."
    return f"{ticker.upper()} is trading at ${price}"


print(f"Tool name:        {get_stock_price.name}")
print(f"Tool description: {get_stock_price.description}")
print(f"Tool args schema: {get_stock_price.args}\n")

TOOLS = [get_stock_price]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)

messages = [
    SystemMessage(content="You are a helpful assistant with access to a stock price tool."),
    HumanMessage(content="What's the price of AAPL right now?"),
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
