"""
Tool Calling.

Shows the two tool types an agent can call:
  - FunctionTool: wraps a plain Python function.
  - QueryEngineTool: wraps a query engine, so retrieval itself becomes
    something an agent chooses to call, rather than a hardcoded step.

Part 1 calls a FunctionTool directly (no LLM involved) to show what a
"tool" actually is under the hood: a name, a description, an argument
schema, and a callable.

Part 2 hands both tools to a ReActAgent and asks a question that can only
be answered by combining them: looking up a policy fact via the
QueryEngineTool, then doing arithmetic on it via the FunctionTool. The
agent decides on its own, from the tool descriptions, which tool(s) to
call and in what order.

ReActAgent is used (rather than a model relying on native function
calling) because it works with any chat-capable model, including the
plain llama3:8b model pulled for these examples. Both the embedding
model and the LLM run locally through Ollama, so no API key is needed.
"""

import asyncio
import os

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def remaining_vacation_days(total_days: float, days_used: float) -> float:
    """Compute how many vacation days remain, given the total allotted and days already used."""
    return total_days - days_used


def build_tools() -> tuple[FunctionTool, QueryEngineTool]:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    calc_tool = FunctionTool.from_defaults(fn=remaining_vacation_days)

    documents = SimpleDirectoryReader(
        input_files=[os.path.join(DATA_DIR, "company_policy.txt")]
    ).load_data()
    vector_index = VectorStoreIndex.from_documents(documents)
    policy_tool = QueryEngineTool.from_defaults(
        query_engine=vector_index.as_query_engine(similarity_top_k=2),
        name="company_policy_search",
        description="Search the company policy document for facts such as vacation, remote work, or expense rules.",
    )

    return calc_tool, policy_tool


async def main():
    calc_tool, policy_tool = build_tools()

    # Part 1: call the FunctionTool directly - no LLM, no agent, just the raw tool.
    print("=== Calling the tool directly (no LLM involved) ===")
    direct_result = calc_tool.call(total_days=18, days_used=5)
    print(f"remaining_vacation_days(total_days=18, days_used=5) -> {direct_result.raw_output}\n")

    # Part 2: let an agent decide, from the tool descriptions, when to call what.
    print("=== Letting an agent choose the tools ===")
    agent = ReActAgent(tools=[calc_tool, policy_tool], llm=Settings.llm, verbose=False)

    question = (
        "First use company_policy_search to find the exact number of vacation "
        "days full-time employees get per year - do not guess this number. "
        "Then use remaining_vacation_days with that exact number and 5 days "
        "already used to compute how many vacation days are left."
    )
    print(f"Q: {question}\n")
    response = await agent.run(question)
    print(f"\nA: {response}")


if __name__ == "__main__":
    asyncio.run(main())
