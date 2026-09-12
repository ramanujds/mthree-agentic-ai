#!/usr/bin/env python3
"""LCEL basics — the pipe operator builds a RunnableSequence.

`prompt | llm | parser` chains three Runnables so each one's output becomes
the next one's input: format a prompt -> send it to the model -> parse the
response into a plain string.

Setup: a local model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run 01_pipe_sequence.py
"""
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)

# 1. Define a template with variables in curly braces
template = "Tell me a {adjective} joke about {content}. Keep it to one sentence."

# 2. Create a prompt template instance
prompt = PromptTemplate.from_template(template)

# 3. Build a chain with the pipe operator: prompt -> llm -> parser
chain = prompt | llm | StrOutputParser()

# 4. Invoke the chain with input values
result = chain.invoke({"adjective": "corny", "content": "databases"})

print(f"Prompt template: {template}")
print(f"Chain type:      {type(chain).__name__}")
print(f"\nResult: {result}")
