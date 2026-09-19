# Step 5 — First Ingestion

> [Back to index](README.md) · Previous: [Loading Documents](05-loading-documents.md) · Next: [Persistence and Reuse](07-persistence-and-reuse.md)

## Goal

Actually chunk, embed, and store the documents into Chroma using `VectorStoreIndex.from_documents`. This step is deliberately naive — it ingests unconditionally, every run — so the next step has a real problem to fix.

## Why this matters

`VectorStoreIndex.from_documents(documents, storage_context=...)` is doing three jobs LlamaIndex hides behind one call: chunking each `Document` into `Node`s (using the default `SentenceSplitter`, since none was configured explicitly), embedding each `Node` with `Settings.embed_model`, and writing each embedded `Node` into whatever vector store the `StorageContext` points at. `StorageContext.from_defaults(vector_store=vector_store)` is what tells `from_documents` to write into Chroma specifically, rather than keeping everything in memory the way [../simple-rag-example](../simple-rag-example/README.md) does.

This version has a real bug, and seeing it matters more than being told about it: because it never checks whether the collection already has data, **running it twice ingests the same two documents twice**, doubling the vector count and leaving duplicate (and therefore competing) chunks in the collection for every future query. That's the exact problem Step 6 exists to fix.

## 1. Import what's needed for ingestion

```python
from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
```

(`StorageContext` and `VectorStoreIndex` are new; `Settings` and `SimpleDirectoryReader` you already have.)

## 2. Ingest into Chroma, unconditionally

Replace the loading/printing code from Step 4 with:

```python
    documents = SimpleDirectoryReader(DATA_DIR).load_data()

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    print(f"Ingested into '{COLLECTION_NAME}'. Vector count: {chroma_collection.count()}")
```

## Try it

Make sure you're starting from an empty collection (`docker compose down -v && docker compose up -d` if you've run earlier steps against this same volume), then run it:

```bash
uv run main.py
```

Expected output — the exact count depends on how the `SentenceSplitter` chunked the two files, but it will be a small positive number:

```
Collection 'onboarding_docs' has 0 vector(s).
Ingested into 'onboarding_docs'. Vector count: 3
```

Now run it again, without resetting anything:

```bash
uv run main.py
```

```
Collection 'onboarding_docs' has 3 vector(s).
Ingested into 'onboarding_docs'. Vector count: 6
```

The count doubled. Every re-run re-embeds and re-inserts the same two documents, growing the collection forever and leaving duplicate chunks that will both show up in future similarity searches.

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
from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
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

    documents = SimpleDirectoryReader(DATA_DIR).load_data()

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    print(f"Ingested into '{COLLECTION_NAME}'. Vector count: {chroma_collection.count()}")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Vector count doesn't double on the second run | Collection was reset between runs (e.g. Docker container recreated without the volume) | Expected if you reset — this demo requires the collection to persist between the two runs |
| `TimeoutError` during ingestion | Embedding 2 short files shouldn't be slow — check Ollama isn't also loading a model for the first time | Wait for the first call to finish loading the model, then retry |
| Vector count is much higher than expected (dozens) | `SentenceSplitter`'s default `chunk_size` is small relative to very long input, or you accidentally ingested unrelated files sitting in `data/` | Check exactly which files are under `data/` |

Next: **[Persistence and Reuse](07-persistence-and-reuse.md)** — fix the duplication bug by checking whether the collection already has data.
