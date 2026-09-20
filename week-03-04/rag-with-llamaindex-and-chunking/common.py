"""
Shared setup for the chunking-strategy examples: local models via Ollama,
a persistent Chroma DB collection per script, and small print helpers so
you can actually see how each strategy split the document.
"""

import os

import chromadb
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

HANDBOOK_PATH = os.path.join(os.path.dirname(__file__), "data", "employee_handbook.md")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))


def load_handbook_text() -> str:
    with open(HANDBOOK_PATH, encoding="utf-8") as f:
        return f.read()


def configure_models():
    """Point LlamaIndex's global Settings at local Ollama models."""
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def get_chroma_collection(name: str):
    """Get (or create) a persistent Chroma collection, one per chunking strategy."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_or_create_collection(name)


def print_nodes(nodes, label: str, preview_chars: int = 160) -> None:
    """Print a compact preview of each node/chunk so strategies can be compared."""
    print(f"\n=== {label}: {len(nodes)} chunk(s) ===")
    for i, node in enumerate(nodes):
        text = node.get_content().strip().replace("\n", " ")
        preview = text[:preview_chars] + ("..." if len(text) > preview_chars else "")
        print(f"[{i}] ({len(text)} chars) {preview}")
    print()


def print_answer(question: str, response, source_nodes=None) -> None:
    print(f"Q: {question}")
    print(f"A: {response}\n")
    if source_nodes is not None:
        for n in source_nodes:
            preview = n.get_content().strip().replace("\n", " ")[:100]
            print(f"  source ({n.score:.3f}): {preview}...")
    print("-" * 60)
