"""
RAG example with LlamaIndex + Qdrant.

Qdrant runs as a separate server (via `docker compose up`) and persists
vectors to disk, unlike the in-memory VectorStoreIndex in the plain
simple-rag-example. Both the embedding model and the LLM run locally
through Ollama, so no API key is needed.
"""

import os

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "onboarding_docs"


def build_query_engine():
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name=COLLECTION_NAME)

    # Unlike Chroma, Qdrant errors if you call count() on a collection that
    # doesn't exist yet, so check existence first.
    needs_ingestion = not qdrant_client.collection_exists(COLLECTION_NAME) or (
        qdrant_client.count(COLLECTION_NAME).count == 0
    )

    if needs_ingestion:
        # Collection is empty (or missing): load, chunk, embed, and persist into Qdrant.
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = SimpleDirectoryReader(DATA_DIR).load_data()
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    else:
        # Collection already has data from a previous run: reuse it.
        index = VectorStoreIndex.from_vector_store(vector_store)

    return index.as_query_engine(similarity_top_k=2)


def main():
    query_engine = build_query_engine()

    questions = [
        "How many days can I work remotely per week?",
        "How do I get a laptop as a new hire?",
        "How many vacation days do I get and can I carry them over?",
    ]

    for question in questions:
        response = query_engine.query(question)
        print(f"Q: {question}")
        print(f"A: {response}\n")
        print("Sources:", [n.node.metadata.get("file_name") for n in response.source_nodes])
        print("-" * 60)


if __name__ == "__main__":
    main()
