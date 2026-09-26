"""
Router Query Engine.

Wraps two query engines over the SAME document set - a SummaryIndex
(good for "summarize everything" questions) and a VectorStoreIndex
(good for "find this specific fact" questions) - behind one
RouterQueryEngine. An LLMSingleSelector reads each tool's description
and decides, per query, which underlying engine should actually answer.

This is the simplest form of "agentic" behavior: a single routing
decision, no iteration, no re-querying. Both the embedding model and the
LLM run locally through Ollama, so no API key is needed.
"""

import os

from llama_index.core import Settings, SimpleDirectoryReader, SummaryIndex, VectorStoreIndex
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def build_router_query_engine() -> RouterQueryEngine:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()

    summary_index = SummaryIndex.from_documents(documents)
    vector_index = VectorStoreIndex.from_documents(documents)

    summary_tool = QueryEngineTool.from_defaults(
        query_engine=summary_index.as_query_engine(),
        name="summary_tool",
        description=(
            "Useful for broad, high-level questions that ask to summarize "
            "or list out everything covered by the company policy and "
            "onboarding documents."
        ),
    )
    vector_tool = QueryEngineTool.from_defaults(
        query_engine=vector_index.as_query_engine(similarity_top_k=2),
        name="vector_tool",
        description=(
            "Useful for retrieving a specific fact or detail from the "
            "company policy or onboarding documents, e.g. a number, a "
            "deadline, or a named contact."
        ),
    )

    return RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=[summary_tool, vector_tool],
        verbose=True,
    )


def main():
    router_query_engine = build_router_query_engine()

    questions = [
        "Give me a summary of everything covered in these documents.",
        "How many vacation days do employees get per year?",
    ]

    for question in questions:
        print(f"Q: {question}")
        response = router_query_engine.query(question)
        print(f"A: {response}\n")

        selector_result = response.metadata.get("selector_result")
        if selector_result is not None:
            for ind, reason in zip(selector_result.inds, selector_result.reasons):
                print(f"  [router chose index {ind}] reason: {reason}")
        print("-" * 60)


if __name__ == "__main__":
    main()
