import os
from pathlib import Path

LLM_MODEL = os.getenv("MARKET_ASSISTANT_MODEL", "llama3:8b")
EMBED_MODEL = os.getenv("MARKET_ASSISTANT_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"

MAX_STEPS = 8
RETRIEVAL_K = 3
