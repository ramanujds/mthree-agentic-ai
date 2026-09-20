"""
RAG example with LlamaIndex + Chroma DB.

Chroma runs as a separate server (via `docker compose up`) and persists
vectors to disk, unlike the in-memory VectorStoreIndex in the plain
simple-rag-example. Both the embedding model and the LLM run locally
through Ollama, so no API key is needed.
"""

import os

import chromadb
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
COLLECTION_NAME = "onboarding_docs"


def build_query_engine():
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        # Collection is empty: load, chunk, embed, and persist into Chroma.
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
