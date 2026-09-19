# Step 6 — Persistence and Reuse

> [Back to index](README.md) · Previous: [First Ingestion](06-first-ingestion.md) · Next: [Query Engine and Sources](08-query-engine-and-sources.md)

## Goal

Fix Step 5's duplication bug: ingest only when the collection is actually empty, and reconnect to existing vectors otherwise. This is the single feature that distinguishes this app from [../simple-rag-example](../simple-rag-example/README.md).

## Why this matters

The fix is one `if`/`else` around a fact you already have on hand: `chroma_collection.count()`. If it's `0`, there's nothing to reuse — ingest normally. If it's not `0`, someone already did that work — usually a previous run of this exact script — so re-embedding would be pure waste (and, as Step 5 showed, actively harmful).

`VectorStoreIndex.from_vector_store(vector_store)` is the other half of the fix: it builds an `index` object that reads from Chroma's existing vectors, without touching `SimpleDirectoryReader`, chunking, or the embedding model at all. This is the concrete payoff of using a real vector store instead of an in-memory one — there is no equivalent "reconnect without re-embedding" path for `simple-rag-example`'s in-memory index, because nothing about it survives past the process that created it.

This is also a natural point to extract the setup logic into its own function, `build_query_engine()`, since `main()` is about to become just "build, then use" — matching the shape every app in this series follows.

## 1. Branch on whether the collection is empty

Replace the unconditional ingestion from Step 5 with a check:

```python
    if chroma_collection.count() == 0:
        # Collection is empty: load, chunk, embed, and persist into Chroma.
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = SimpleDirectoryReader(DATA_DIR).load_data()
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    else:
        # Collection already has data from a previous run: reuse it.
        index = VectorStoreIndex.from_vector_store(vector_store)
```

Notice document loading moved *inside* the `if` branch — there's no reason to read the files from disk at all when you're just reconnecting to vectors that already exist.

## 2. Extract the setup into `build_query_engine()`

Move everything up to and including the branch above into its own function, and have `main()` just call it:

```python
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

    return index


def main():
    index = build_query_engine()
    print("Index ready:", index)
```

## Try it

Reset to a clean slate so you can see both paths:

```bash
docker compose down -v && docker compose up -d
```

First run — the collection is empty, so it ingests:

```bash
uv run main.py
```

```
Index ready: <llama_index.core.indices.vector_store.base.VectorStoreIndex object at 0x...>
```

Run it a second time — this time watch how much faster it returns, and (if you have Ollama's logs open) that no new embedding requests are made:

```bash
uv run main.py
```

Same printed line, but noticeably faster — the second run never calls `SimpleDirectoryReader` or the embedding model at all. Confirm the vector count didn't change:

```bash
curl -s http://localhost:8000/api/v2/heartbeat > /dev/null && echo "Chroma is up"
```

(Or simply keep the count-printing line from Step 5 temporarily if you want to see the number directly — it's fine to leave it in while you're verifying this, then remove it for Step 7's cleaner version.)

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

    return index


def main():
    index = build_query_engine()
    print("Index ready:", index)


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Second run still re-ingests | `chroma_collection.count()` checked *before* the first run's `docker compose up`, on a stale collection reference | Make sure `chroma_collection` is fetched fresh each call to `build_query_engine()`, not cached across runs |
| Edited a file in `data/` but the answer doesn't reflect the change | The collection already has data, so the `else` branch runs and the file is never re-read | Expected — force re-ingestion with `docker compose down -v && docker compose up -d` |
| `from_vector_store` raises about missing embedding dimension | Switched `EMBED_MODEL` between runs without resetting the collection | Vectors from different embedding models aren't interchangeable — reset the collection when you change embedding models |

Next: **[Query Engine and Sources](08-query-engine-and-sources.md)** — turn this index into something that actually answers questions.
