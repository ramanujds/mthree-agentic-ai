"""
Simple RAG example with LlamaIndex.

No vector database, no LangChain: VectorStoreIndex holds vectors
in-memory
"""

import os
import sys

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def build_query_engine():
    Settings.llm = Ollama(model="llama3:8b", base_url="http://localhost:11434", request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")

    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    index = VectorStoreIndex.from_documents(documents)  # in-memory, no vector DB

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
