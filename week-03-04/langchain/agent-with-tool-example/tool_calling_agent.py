#!/usr/bin/env python3
"""ToolCallingAgent — companion code for ../langchain-advanced/interactive-agents.md.

Encapsulates the manual tool-calling loop (bind tools -> inspect AIMessage.tool_calls
-> execute -> append ToolMessage -> re-invoke) into a reusable class that owns its
own chat_history, so multi-turn conversations "just work" across calls.

Setup: a local Gemma model via Docker Model Runner (see
../../code/00-local-model-setup/README.md).

Run:
    uv run tool_calling_agent.py
"""
import os

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
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


class ToolCallingAgent:
    """Owns chat history and the model-tool loop, so callers just call .invoke(query)."""

    def __init__(self, llm: ChatOpenAI, tools: list, system_message: str | None = None, max_steps: int = 5):
        self.tool_map = {t.name: t for t in tools}
        self.llm_with_tools = llm.bind_tools(tools)
        self.max_steps = max_steps
        self.chat_history: list[BaseMessage] = []
        if system_message:
            self.chat_history.append(SystemMessage(content=system_message))

    def invoke(self, query: str) -> str:
        self.chat_history.append(HumanMessage(content=query))

        ai_msg: AIMessage = self.llm_with_tools.invoke(self.chat_history)
        self.chat_history.append(ai_msg)

        steps = 0
        while ai_msg.tool_calls and steps < self.max_steps:
            for call in ai_msg.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]
                tool_id = call["id"]

                result = self.tool_map[tool_name].invoke(tool_args)
                print(f"  -> called {tool_name}({tool_args}) = {result}")

                self.chat_history.append(ToolMessage(content=str(result), tool_call_id=tool_id))

            ai_msg = self.llm_with_tools.invoke(self.chat_history)
            self.chat_history.append(ai_msg)
            steps += 1

        return ai_msg.content


if __name__ == "__main__":
    llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)

    agent = ToolCallingAgent(
        llm=llm,
        tools=[add, subtract, multiply, divide],
        system_message="You are a helpful assistant with access to arithmetic tools.",
    )

    queries = [
        "What is 3 plus 2?",
        "1 minus 2",              # imprecise / informal phrasing
        "and now multiply that by 10",
    ]

    for q in queries:
        print(f"\nUser: {q}")
        print(f"Agent: {agent.invoke(q)}")
