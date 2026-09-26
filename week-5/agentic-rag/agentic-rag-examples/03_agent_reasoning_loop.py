"""
Agent Reasoning Loop.

Same two tools as 02_tool_calling.py, but this script makes the
underlying reason -> act -> observe -> repeat loop visible by streaming
the agent's internal events instead of only printing the final answer.

The question is deliberately written to require TWO sequential tool
calls, where the second call's arguments depend on the first call's
result - a multi-step chain the agent has to plan on its own:
  1. Look up the total vacation day allowance (QueryEngineTool).
  2. Subtract the days already used (FunctionTool), using the number
     found in step 1.

ReActAgent is used because it works with any chat-capable model,
including the plain llama3:8b model pulled for these examples. Both the
embedding model and the LLM run locally through Ollama, so no API key is
needed.
"""

import asyncio
import os

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.agent.workflow import ReActAgent, ToolCall, ToolCallResult
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


def build_agent() -> ReActAgent:
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

    return ReActAgent(tools=[calc_tool, policy_tool], llm=Settings.llm, verbose=False)


async def main():
    agent = build_agent()

    question = (
        "Use company_policy_search to look up the total number of vacation "
        "days full-time employees get per year - do not guess this number. "
        "Then use remaining_vacation_days to tell me how many are left if "
        "someone has already used 7 days."
    )
    print(f"Q: {question}\n")

    handler = agent.run(question)
    step = 0

    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            step += 1
            print(f"[step {step}] ACTION   -> {event.tool_name}(kwargs={event.tool_kwargs})")
        elif isinstance(event, ToolCallResult):
            print(f"[step {step}] OBSERVE  -> {event.tool_output.content}")

    response = await handler
    print(f"\nFinal answer: {response}")


if __name__ == "__main__":
    asyncio.run(main())
