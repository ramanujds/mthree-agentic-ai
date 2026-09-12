#!/usr/bin/env python3
"""LCEL data manipulation — RunnablePassthrough.assign() for a mini RAG shape.

`RunnablePassthrough.assign(context=...)` takes the incoming dict, adds a new
"context" key computed from it, and keeps every original key too. That lets a
prompt further down the chain see both the original question and the
retrieved context, without a wrapper class.

Setup: a local model via Docker Model Runner (see
../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/api_key
for a hosted provider if you'd rather use one.

Run:
    uv run 04_passthrough_assign.py
"""
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)

# Stand-in for a real retriever — looks up "documents" from a tiny in-memory store.
DOCS = {
    "lcel": "LCEL is LangChain's declarative syntax for composing Runnables with the pipe operator.",
    "langgraph": "LangGraph is LangChain's library for building stateful, graph-based multi-step agents.",
}


def fake_retriever(inputs: dict) -> str:
    question = inputs["question"].lower()
    for keyword, doc in DOCS.items():
        if keyword in question:
            return doc
    return "No matching document found."


prompt = PromptTemplate.from_template(
    "Answer the question using only the context below.\n\nContext: {context}\n\nQuestion: {question}\nAnswer:"
)

# assign() adds "context" while keeping "question" — prompt needs both.
rag_chain = (
    RunnablePassthrough.assign(context=RunnableLambda(fake_retriever))
    | prompt
    | llm
    | StrOutputParser()
)

question = "What is LCEL?"
enriched_input = RunnablePassthrough.assign(context=RunnableLambda(fake_retriever)).invoke({"question": question})

print(f"Original input:  {{'question': {question!r}}}")
print(f"After assign():  {enriched_input}\n")

result = rag_chain.invoke({"question": question})
print(f"Result: {result}")
