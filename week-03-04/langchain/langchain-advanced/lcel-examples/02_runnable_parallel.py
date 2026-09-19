#!/usr/bin/env python3
"""LCEL type coercion — a dict of chains becomes a RunnableParallel.

Each value in the dict is its own `prompt | llm` chain. Piping that dict into
the next step (here, a RunnableLambda that formats a report) makes LCEL
coerce the dict into a RunnableParallel: all three chains run concurrently
against the *same* input, and their outputs land under matching keys for the
next step to consume. A bare dict has no .invoke() of its own — the
coercion only happens once it is used as a step in a chain.

Setup: a local model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run 02_runnable_parallel.py
"""
import os
import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
parser = StrOutputParser()

summary_chain = PromptTemplate.from_template("Summarize this in one short sentence:\n{text}") | llm | parser
translation_chain = PromptTemplate.from_template("Translate this to Hindi:\n{text}") | llm | parser
sentiment_chain = PromptTemplate.from_template("Reply with one word: positive, negative, or neutral.\n{text}") | llm | parser

def format_report(outputs: dict) -> str:
    return "\n".join(f"{key:>11}: {value}" for key, value in outputs.items())


# Piping this dict into format_report auto-coerces it into a RunnableParallel
# — every branch receives the same {"text": ...} input and runs concurrently.
analysis_chain = {
    "summary": summary_chain,
    "translation": translation_chain,
    "sentiment": sentiment_chain,
} | RunnableLambda(format_report)

print(f"Coerced parallel step type: {type(analysis_chain.first).__name__}")

text = "LangChain's LCEL makes it easy to compose LLM pipelines with a simple pipe operator."

start = time.perf_counter()
result = analysis_chain.invoke({"text": text})
elapsed = time.perf_counter() - start

print(f"\nInput text: {text}\n\n{result}")
print(f"\nAll three branches ran concurrently in {elapsed:.2f}s.")
