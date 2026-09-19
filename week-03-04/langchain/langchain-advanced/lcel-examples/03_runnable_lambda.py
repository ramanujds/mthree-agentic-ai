#!/usr/bin/env python3
"""LCEL type coercion — a plain function becomes a RunnableLambda.

`RunnableLambda(format_prompt)` wraps an ordinary Python function so it can
sit in a pipe chain like any other Runnable: it takes the input dict, runs
custom logic, and passes its return value on to the next component.

Setup: a local model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run 03_runnable_lambda.py
"""
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)


def format_prompt(inputs: dict) -> str:
    """Custom business logic — plain Python, no LangChain types involved."""
    return f"Tell me a {inputs['adjective']} joke about {inputs['content']}. Keep it to one sentence."


# RunnableLambda -> llm -> StrOutputParser, connected with the pipe operator.
joke_chain = RunnableLambda(format_prompt) | llm | StrOutputParser()

result = joke_chain.invoke({"adjective": "silly", "content": "parrots"})

print(f"format_prompt() built: {format_prompt({'adjective': 'silly', 'content': 'parrots'})!r}")
print(f"\nResult: {result}")
