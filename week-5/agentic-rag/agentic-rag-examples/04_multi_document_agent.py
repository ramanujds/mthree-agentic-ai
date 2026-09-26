"""
Multi-Document Agent.

Three short "papers" with a citation chain (paper_agents cites
paper_rag, which cites paper_llm - the same dataset used by the
Recursive Retriever example in ../advanced-retrievers-examples) are each
given their own pair of tools:
  - a vector_tool for pulling specific facts out of that one paper
  - a summary_tool for a high-level summary of that one paper

That's 6 tools total. Rather than stuffing all 6 descriptions into the
agent's prompt directly (which stops scaling once you have hundreds of
documents), the tools are indexed in an ObjectIndex - a vector index
built OVER THE TOOLS THEMSELVES - so the agent retrieves only the
top-k most relevant tools for each query. The agent then runs its usual
reasoning loop (see 03_agent_reasoning_loop.py) over just that shortlist.

The question below can't be answered by any single paper: it requires
pulling a fact from paper_llm, a fact from paper_rag, and a fact from
paper_agents, then synthesizing across all three. Both the embedding
model and the LLM run locally through Ollama, so no API key is needed.
"""

import asyncio
import os

from llama_index.core import Settings, SimpleDirectoryReader, SummaryIndex, VectorStoreIndex
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.objects import ObjectIndex
from llama_index.core.tools import QueryEngineTool
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "papers")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

PAPERS = {
    "paper_llm": "Scaling Transformer-Based Language Models",
    "paper_rag": "Retrieval-Augmented Generation for Knowledge-Intensive Tasks",
    "paper_agents": "Agentic Systems: Planning and Tool Use on Top of Retrieval-Augmented Models",
}


def build_per_document_tools() -> list[QueryEngineTool]:
    tools = []
    for doc_name, title in PAPERS.items():
        documents = SimpleDirectoryReader(
            input_files=[os.path.join(DATA_DIR, f"{doc_name}.txt")]
        ).load_data()

        vector_index = VectorStoreIndex.from_documents(documents)
        summary_index = SummaryIndex.from_documents(documents)

        tools.append(
            QueryEngineTool.from_defaults(
                query_engine=vector_index.as_query_engine(similarity_top_k=2),
                name=f"vector_tool_{doc_name}",
                description=f'Look up a specific fact or detail from the paper "{title}" ({doc_name}).',
            )
        )
        tools.append(
            QueryEngineTool.from_defaults(
                query_engine=summary_index.as_query_engine(),
                name=f"summary_tool_{doc_name}",
                description=f'Get a high-level summary of the paper "{title}" ({doc_name}).',
            )
        )
    return tools


def build_top_level_agent() -> tuple[ReActAgent, ObjectIndex]:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    all_tools = build_per_document_tools()
    print(f"Built {len(all_tools)} per-document tools across {len(PAPERS)} papers.\n")

    # Index the tools themselves, so the agent only ever sees the top-k
    # most relevant tools for a given query instead of all of them.
    tool_object_index = ObjectIndex.from_objects(all_tools, index_cls=VectorStoreIndex)
    tool_retriever = tool_object_index.as_retriever(similarity_top_k=4)

    agent = ReActAgent(tool_retriever=tool_retriever, llm=Settings.llm, verbose=False)
    return agent, tool_object_index


async def main():
    agent, tool_object_index = build_top_level_agent()

    question = (
        "What key limitation of large language models does retrieval-augmented "
        "generation address, and what further capability do agentic systems add "
        "on top of retrieval-augmented generation?"
    )
    print(f"Q: {question}\n")

    # Show which tools the object index considered relevant for this query,
    # before letting the agent actually run its reasoning loop over them.
    shortlisted = tool_object_index.as_retriever(similarity_top_k=4).retrieve(question)
    print("Tools shortlisted by the object index for this query:")
    for t in shortlisted:
        print(f"  - {t.metadata.name}")
    print()

    response = await agent.run(question)
    print(f"A: {response}")


if __name__ == "__main__":
    asyncio.run(main())
