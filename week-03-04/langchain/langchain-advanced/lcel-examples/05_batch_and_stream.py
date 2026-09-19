#!/usr/bin/env python3
"""LCEL execution modes — invoke() vs. batch() vs. stream().

Every LCEL chain shares the same Runnable interface, so the exact same
`chain` object can be run three different ways: one input at a time
(invoke), many inputs at once (batch), or token-by-token as they're
generated (stream) — no extra code needed per mode.

Setup: a local model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run 05_batch_and_stream.py
"""
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
chain = PromptTemplate.from_template("Name one fun fact about {topic}. One sentence.") | llm | StrOutputParser()

# invoke() — one input, one output.
print("=== invoke() ===")
print(chain.invoke({"topic": "octopuses"}))

# batch() — many inputs, processed in parallel, results in the same order.
print("\n=== batch() ===")
topics = [{"topic": "the moon"}, {"topic": "coffee"}, {"topic": "penguins"}]
results = chain.batch(topics)
for topic, result in zip(topics, results):
    print(f"{topic['topic']:>10}: {result}")

# stream() — incremental chunks as the model generates them.
print("\n=== stream() ===")
for chunk in chain.stream({"topic": "black holes"}):
    print(chunk, end="", flush=True)
print()
