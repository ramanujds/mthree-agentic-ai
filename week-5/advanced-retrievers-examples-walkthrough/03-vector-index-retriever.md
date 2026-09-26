# Step 2 — Vector Index Retriever

> [Back to index](README.md) · Previous: [Environment Setup](02-environment-setup.md) · Next: [BM25 Retriever](04-bm25-retriever.md)

## Goal

Build `01_vector_index_retriever.py`: the baseline semantic retriever every other script in this walkthrough will be compared against.

## Why this matters

A `VectorStoreIndex` holds embeddings; a `VectorIndexRetriever` is the (small, stateless) object that actually runs similarity search against it with a given `similarity_top_k`. Calling `index.as_retriever(similarity_top_k=2)` would return the exact same kind of object — this script constructs `VectorIndexRetriever` directly instead, so you see the class name every other index's `.as_retriever()` is quietly returning under the hood.

The other thing worth noticing up front: `retriever.retrieve(question)` never calls an LLM. It embeds the question, does a similarity search, and returns `NodeWithScore` objects. Nothing here reads or writes `Settings.llm` — only `Settings.embed_model` is actually exercised, even though this script (and most others in this walkthrough) sets both.

## 1. Scaffold the file

```python
"""
Vector Index Retriever.

The default, general-purpose retriever: it embeds the query, does a
similarity search over an in-memory VectorStoreIndex, and returns the
top-k semantically closest chunks. Both the embedding model and the LLM
run locally through Ollama, so no API key is needed.
"""

import os

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

Save this as `01_vector_index_retriever.py`. As with every script here, configuration is read from environment variables with local defaults, so nothing is hardcoded to one machine.

## 2. Build the retriever

Replace `main()`'s body — for now, add `build_retriever()` above it and leave `main()` calling `print("Scaffold ready.")`:

```python
def build_retriever() -> VectorIndexRetriever:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()
    index = VectorStoreIndex.from_documents(documents)

    # Retriever only: no LLM call happens on .retrieve(), just embedding + similarity search.
    return VectorIndexRetriever(index=index, similarity_top_k=2)
```

Notice `input_files=[...]` names the two files explicitly, rather than pointing `SimpleDirectoryReader` at `DATA_DIR` as a whole. Later steps will add more files to `data/` (a long handbook, three "papers") that this script has no business ingesting — being explicit here means this script's behavior never silently changes just because `data/` grew.

`Settings.embed_model` has to be set before `VectorStoreIndex.from_documents` runs — LlamaIndex's default embedding model expects an OpenAI API key, and this project has none, so skipping this line fails loudly (see Common mistakes below).

## 3. Retrieve and print results

```python
def main():
    retriever = build_retriever()

    questions = [
        "How many vacation days do employees get?",
        "What should I do if my laptop hasn't arrived yet?",
    ]

    for question in questions:
        nodes = retriever.retrieve(question)
        print(f"Q: {question}")
        for n in nodes:
            print(f"  score={n.score:.4f} file={n.node.metadata.get('file_name')}")
            print(f"  text: {n.node.get_content()[:120]}...")
        print("-" * 60)
```

Each `NodeWithScore` carries the retrieved `node` (with its text and metadata, including which source file it came from) and a `score` — here, cosine similarity between the question's embedding and the chunk's embedding.

## Try it

```bash
uv run 01_vector_index_retriever.py
```

Expected output (embeddings are deterministic, so these scores should reproduce exactly):

```
Q: How many vacation days do employees get?
  score=0.7399 file=company_policy.txt
  text: Remote Work Policy

Employees may work remotely up to 3 days per week, subject to manager
approval. Requests must be sub...
  score=0.5297 file=onboarding_faq.txt
  text: Onboarding FAQ

Q: How do I get a laptop?
A: New hires receive a laptop on their first day, shipped by the IT
department...
------------------------------------------------------------
Q: What should I do if my laptop hasn't arrived yet?
  score=0.5706 file=onboarding_faq.txt
  ...
```

Both source files are short enough to become a single chunk each, so every question retrieves "the whole file" for both results — the top-ranked one just happens to be the more relevant file. You'll see multiple chunks *within* one file for the first time in later steps, once documents are long enough to actually split.

## Checkpoint

<details>
<summary>Full <code>01_vector_index_retriever.py</code></summary>

```python
"""
Vector Index Retriever.

The default, general-purpose retriever: it embeds the query, does a
similarity search over an in-memory VectorStoreIndex, and returns the
top-k semantically closest chunks. Both the embedding model and the LLM
run locally through Ollama, so no API key is needed.
"""

import os

from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def build_retriever() -> VectorIndexRetriever:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()
    index = VectorStoreIndex.from_documents(documents)

    # Retriever only: no LLM call happens on .retrieve(), just embedding + similarity search.
    return VectorIndexRetriever(index=index, similarity_top_k=2)


def main():
    retriever = build_retriever()

    questions = [
        "How many vacation days do employees get?",
        "What should I do if my laptop hasn't arrived yet?",
    ]

    for question in questions:
        nodes = retriever.retrieve(question)
        print(f"Q: {question}")
        for n in nodes:
            print(f"  score={n.score:.4f} file={n.node.metadata.get('file_name')}")
            print(f"  text: {n.node.get_content()[:120]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
```

This matches [../advanced-retrievers-examples/01_vector_index_retriever.py](../advanced-retrievers-examples/01_vector_index_retriever.py) exactly.

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `openai.OpenAIError: The api_key client option must be set` | Forgot to set `Settings.embed_model` before building the index | Set both `Settings.llm` and `Settings.embed_model` at the top of `build_retriever()`, before any index is created |
| Both questions always return the exact same two nodes in the same order | Corpus is only 2 short files; expected at this stage | Add more/longer files to see ranking actually change between questions |
| A future script's data leaks into this one's results | Used `SimpleDirectoryReader(DATA_DIR)` instead of `input_files=[...]` | Always list the exact files a script needs, as shown above |

Next: **[BM25 Retriever](04-bm25-retriever.md)** — same shape, but ranking by keywords instead of meaning.
