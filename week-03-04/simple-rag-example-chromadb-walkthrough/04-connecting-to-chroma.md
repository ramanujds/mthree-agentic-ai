# Step 3 — Connecting to Chroma

> [Back to index](README.md) · Previous: [Configure Ollama Settings](03-configure-ollama-settings.md) · Next: [Loading Documents](05-loading-documents.md)

## Goal

Connect to the Chroma server from Step 1, create (or reuse) a named collection, and wrap it in the adapter LlamaIndex needs to treat it as a vector store — with no documents or embeddings involved yet.

## Why this matters

A **collection** in Chroma is the unit everything else attaches to — similar to a table in a relational database. `get_or_create_collection` is deliberately idempotent: call it once against an empty database and it creates the collection; call it again later against a database that already has it, and it just hands back the existing one. That idempotency is exactly what will let this app be re-run safely in Step 6 — the connection code never needs to know whether this is the first run or the hundredth.

`ChromaVectorStore` is an adapter, not a new database: it wraps a `chromadb` collection object so that LlamaIndex's `VectorStoreIndex` can read and write to it the same way it would to any other supported vector store. Isolating the connection step here — before wiring in documents — means a Chroma connectivity problem shows up as a connectivity problem, not tangled up with a document-loading or embedding error.

## 1. Import the Chroma pieces

```python
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
```

## 2. Add Chroma configuration constants

Next to the Ollama constants, following the same environment-variable-with-a-default pattern:

```python
CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
COLLECTION_NAME = "onboarding_docs"
```

`COLLECTION_NAME` isn't overridable by environment variable here — it's a fixed identifier for *this app's* data within Chroma, not a piece of deployment configuration like the host or port.

## 3. Connect, and inspect the (empty) collection

Replace the smoke-test lines from Step 2 with the Chroma connection:

```python
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    print(f"Collection '{COLLECTION_NAME}' has {chroma_collection.count()} vector(s).")
```

`chromadb.HttpClient` talks to the Chroma server over HTTP — this is the client-server mode from Step 0, not an embedded database inside your Python process.

## Try it

```bash
uv run main.py
```

Expected output on a fresh Chroma instance:

```
Collection 'onboarding_docs' has 0 vector(s).
```

Run it again — the count should still read `0`. `get_or_create_collection` found the collection this run created and reused it, rather than erroring or creating a second one.

## Checkpoint

<details>
<summary>Full <code>main.py</code></summary>

```python
"""
RAG example with LlamaIndex + Chroma DB.

Chroma runs as a separate server (via `docker compose up`) and persists
vectors to disk, unlike the in-memory VectorStoreIndex in the plain
simple-rag-example. Both the embedding model and the LLM run locally
through Ollama, so no API key is needed.
"""

import os

import chromadb
from llama_index.core import Settings
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


def main():
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    print(f"Collection '{COLLECTION_NAME}' has {chroma_collection.count()} vector(s).")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: Could not connect to a Chroma server` | Chroma container isn't running, or `CHROMA_PORT` is wrong | `docker compose ps`; confirm `curl http://localhost:8000/api/v2/heartbeat` responds |
| Count is non-zero on a "fresh" instance | A previous run already ingested data into this collection | Expected once you reach Step 5 — reset with `docker compose down -v && docker compose up -d` if you want a truly empty collection |
| `ImportError` for `chromadb` or `ChromaVectorStore` | Dependency missing | Confirm `chromadb` and `llama-index-vector-stores-chroma` are both in `pyproject.toml`, then `uv sync` |

Next: **[Loading Documents](05-loading-documents.md)** — bring the sample onboarding files into LlamaIndex so there's something to embed.
