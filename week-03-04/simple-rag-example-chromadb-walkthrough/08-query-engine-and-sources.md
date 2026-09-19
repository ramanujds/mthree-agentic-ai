# Step 7 — Query Engine and Sources

> [Back to index](README.md) · Previous: [Persistence and Reuse](07-persistence-and-reuse.md) · Next: [Recap and Exercises](09-recap-and-exercises.md)

## Goal

Turn the `index` from Step 6 into a query engine that actually answers questions, ask it the app's three sample questions, and print which source file grounded each answer.

## Why this matters

`index.as_query_engine(...)` bundles two things you haven't built explicitly: a **retriever** (runs similarity search against Chroma for a given question) and a **response synthesizer** (feeds the retrieved chunks and the question to `Settings.llm` and returns the answer). `.query(question)` runs both in one call.

`similarity_top_k=2` controls how many chunks the retriever pulls back per question. Too low and the answer might miss a relevant chunk that didn't quite rank first; too high and you're feeding the LLM irrelevant context that can dilute or confuse the answer. Two is enough for this app's tiny two-document corpus — a larger corpus would need this tuned.

`response.source_nodes` is what makes a RAG answer *trustworthy* rather than just plausible: it's the actual list of chunks the answer was grounded in, each carrying the metadata (like `file_name`) from Step 4. Printing it turns "trust me" into "here's exactly where this came from" — the single biggest practical difference between a RAG answer and an ungrounded LLM guess.

## 1. Return a query engine instead of a bare index

Change `build_query_engine()`'s return statement:

```python
    return index.as_query_engine(similarity_top_k=2)
```

## 2. Ask the sample questions and print sources

Replace `main()`'s placeholder print with the real question loop:

```python
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
```

`response.source_nodes` is a list of `NodeWithScore` objects; `n.node.metadata` is the same metadata dict you inspected back in Step 4, which is why `file_name` is available here without any extra plumbing.

## Try it

```bash
uv run main.py
```

Expected shape of the output (exact answer wording will vary since it comes from a live LLM; the sources should not):

```
Q: How many days can I work remotely per week?
A: You can work remotely up to 3 days per week, subject to manager approval.

Sources: ['company_policy.txt']
------------------------------------------------------------
Q: How do I get a laptop as a new hire?
A: New hires receive a laptop on their first day, shipped by the IT department.

Sources: ['onboarding_faq.txt']
------------------------------------------------------------
Q: How many vacation days do I get and can I carry them over?
A: You accrue 18 days of paid vacation per year, and can carry over up to 5 unused days to the next year.

Sources: ['company_policy.txt']
------------------------------------------------------------
```

Each answer's source file should make intuitive sense given which document actually contains that information — that alignment is the whole pipeline working correctly end to end.

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
```

</details>

This matches [../simple-rag-example-chromadb/main.py](../simple-rag-example-chromadb/main.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Sources: [None]` | Ingested documents that lost their metadata (e.g. built from raw strings instead of `SimpleDirectoryReader`) | Confirm ingestion used `SimpleDirectoryReader`, not manually constructed `Document` objects |
| Answer references a file that seems unrelated to the question | `similarity_top_k` pulled in a weakly-related chunk because nothing more relevant existed | Try rephrasing the question, or raise `similarity_top_k` to give the retriever more candidates |
| Response text is empty or `None` | LLM call itself failed (timeout, model not loaded) rather than a retrieval problem | Check Ollama logs; retrieval and generation failures print differently — this app doesn't currently catch generation errors explicitly |
| Answers stay stale after editing `data/` files | Collection already has data, so ingestion is skipped (Step 6's `else` branch) | `docker compose down -v && docker compose up -d` to force re-ingestion |

Next: **[Recap and Exercises](09-recap-and-exercises.md)**.
