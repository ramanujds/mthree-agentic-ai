#!/usr/bin/env python3
"""Manual tool-calling calculator agent — companion code for ../agent-with-tool.md.

Demonstrates the full loop, not just a single tool extraction:
  1. Bind arithmetic tools (add/subtract/multiply/divide) to the model.
  2. Let the model request one or more tool calls.
  3. Dispatch each call dynamically via a name -> tool mapping.
  4. Feed each result back as a ToolMessage and re-invoke, until the model
     replies with plain text.
  5. Preserve the running message list across turns for multi-turn memory.

Setup: a local Gemma model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run calculator_agent.py
"""
import os

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")


@tool
def add(a: float, b: float) -> float:
    """Add a and b."""
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply a and b."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    return a / b


TOOLS = [add, subtract, multiply, divide]
TOOL_MAP = {t.name: t for t in TOOLS}

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)


def run_agent(query: str, messages: list[BaseMessage], max_steps: int = 5) -> str:
    """Manual tool-calling agent loop with multi-step + multi-turn support."""
    messages.append(HumanMessage(content=query))

    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)

    steps = 0
    while ai_msg.tool_calls and steps < max_steps:
        for call in ai_msg.tool_calls:
            selected_tool = TOOL_MAP[call["name"]]
            result = selected_tool.invoke(call["args"])
            print(f"  -> called {call['name']}({call['args']}) = {result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)
        steps += 1

    return ai_msg.content


if __name__ == "__main__":
    history: list[BaseMessage] = [
        SystemMessage(content="You are a helpful assistant with access to arithmetic tools.")
    ]

    queries = [
        "What is 3 plus 2?",
        "What is (3 + 2) times 4?",
        "Now divide that by 5.",
    ]

    for q in queries:
        print(f"\nUser: {q}")
        answer = run_agent(q, history)
        print(f"Agent: {answer}")
