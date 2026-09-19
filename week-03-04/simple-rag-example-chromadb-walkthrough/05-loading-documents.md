# Step 4 — Loading Documents

> [Back to index](README.md) · Previous: [Connecting to Chroma](04-connecting-to-chroma.md) · Next: [First Ingestion](06-first-ingestion.md)

## Goal

Load the two sample text files from `data/` into LlamaIndex `Document` objects, and inspect what a `Document` actually contains — before embedding or storing anything.

## Why this matters

`SimpleDirectoryReader` is doing more than "read some files": it's the boundary between your raw files and everything LlamaIndex knows how to do afterwards. Every `Document` it produces carries metadata (like the source filename) alongside the text — and that metadata is exactly what will let the finished app tell you *which file* an answer was grounded in. If you skip inspecting this now, "Sources: [...]" in the final output will feel like it appeared from nowhere; seeing `file_name` in the metadata here makes that connection obvious later.

## 1. Import the reader

```python
from llama_index.core import SimpleDirectoryReader
```

## 2. Load and inspect the documents

Add this temporarily after the Chroma connection code, so you can see what got loaded before wiring it into anything:

```python
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    print(f"Loaded {len(documents)} document(s):")
    for doc in documents:
        print(f" - {doc.metadata.get('file_name')} ({len(doc.text)} chars)")
```

`SimpleDirectoryReader(DATA_DIR).load_data()` always returns a `list[Document]` — one entry per file in `DATA_DIR`, regardless of file type (plain text here, but it handles Markdown, PDF, CSV, and more the same way).

## Try it

```bash
uv run main.py
```

Expected output (exact character counts may differ slightly by a few characters depending on line endings):

```
Collection 'onboarding_docs' has 0 vector(s).
Loaded 2 document(s):
 - company_policy.txt (612 chars)
 - onboarding_faq.txt (628 chars)
```

Two documents, matching the two files in `data/` — nothing has been chunked, embedded, or stored yet.

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
from llama_index.core import Settings, SimpleDirectoryReader
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
    print(f"Loaded {len(documents)} document(s):")
    for doc in documents:
        print(f" - {doc.metadata.get('file_name')} ({len(doc.text)} chars)")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: No files found` | `DATA_DIR` points at the wrong path, or `data/` is empty | Confirm `data/company_policy.txt` and `data/onboarding_faq.txt` exist relative to `main.py` |
| Only 1 document loaded | A file has an extension `SimpleDirectoryReader` doesn't recognize, or is empty | Confirm both files have a `.txt` extension and non-empty content |
| `doc.metadata.get('file_name')` prints `None` | Files were passed via `input_files` with a stream/buffer instead of a path | Not applicable here since we pass a directory path — flag if you've customized the loader call |

Next: **[First Ingestion](06-first-ingestion.md)** — embed these documents and store the vectors in Chroma.
