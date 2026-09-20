# Step 2 — Shared Scaffolding

> [Back to index](README.md) · Previous: [Environment Setup](02-environment-setup.md) · Next: [Fixed-Size Chunking](04-fixed-size-chunking.md)

## Goal

Build `common.py`: the module all six chunking scripts import for local-model configuration, a per-strategy Chroma collection, and print helpers that make chunk boundaries visible.

## Why this matters

Every one of the six scripts you're about to build needs the exact same four things: Ollama models wired up, a way to load the sample document, a Chroma collection to store into, and a way to print out what the chunker actually did. If each script repeated that setup inline, six near-identical copies of the same boilerplate would bury the one line that's actually different per script — the chunking strategy itself.

Pulling this into a shared module does more than avoid repetition: it means when you read `01_fixed_size_chunking.py` through `06_markdown_structure_aware.py` later, everything that isn't imported from `common` *is* the interesting difference between strategies. That's the whole point of comparing them side by side.

The `print_nodes` helper specifically exists because chunking strategies are easy to misjudge by just reading about them — actually seeing "chunk 3 starts mid-sentence" or "chunk 5 is one lonely sentence" is what makes the trade-offs in [../vector-dbs/chunking.md](../vector-dbs/chunking.md) concrete instead of abstract.

## 1. Constants and the document loader

```python
"""
Shared setup for the chunking-strategy examples: local models via Ollama,
a persistent Chroma DB collection per script, and small print helpers so
you can actually see how each strategy split the document.
"""

import os

HANDBOOK_PATH = os.path.join(os.path.dirname(__file__), "data", "employee_handbook.md")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))


def load_handbook_text() -> str:
    with open(HANDBOOK_PATH, encoding="utf-8") as f:
        return f.read()
```

Same pattern as every other app in this series: every configurable value reads from an environment variable with a local-friendly default, so nothing here is hardcoded to one machine.

## 2. Model configuration

```python
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama


def configure_models():
    """Point LlamaIndex's global Settings at local Ollama models."""
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
```

Each of the six scripts calls `configure_models()` once, at the top of `main()`, exactly like [simple-rag-example-chromadb](../rag-with-LlamaIndex/simple-rag-example-chromadb-walkthrough/03-configure-ollama-settings.md) does inline. Pulling it into a function here just means six scripts share one line instead of six copies of the same two-line setup.

## 3. The Chroma collection helper

```python
import chromadb


def get_chroma_collection(name: str):
    """Get (or create) a persistent Chroma collection, one per chunking strategy."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_or_create_collection(name)
```

Taking `name` as a parameter — rather than hardcoding one `COLLECTION_NAME` here — is what lets each script use its own collection (`chunking_fixed_size`, `chunking_sentence_splitter`, and so on). Without separate collections, all six scripts would pile their differently-shaped chunks into the same collection, and comparing retrieval quality between strategies would be meaningless.

## 4. Print helpers

```python
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
```

`print_nodes` is the function that does the actual teaching in this walkthrough — every script calls it right after chunking, before any embedding or querying happens, so you see the raw split *before* anything else can obscure it. `print_answer` mirrors the source-printing pattern from [simple-rag-example-chromadb's Step 7](../rag-with-LlamaIndex/simple-rag-example-chromadb-walkthrough/08-query-engine-and-sources.md), but also prints each source's similarity score, which becomes useful for comparing retrieval confidence across strategies later.

## Try it

`common.py` has no `main()` of its own — it's a library the six scripts import — so smoke-test it directly from the command line:

```bash
uv run python -c "
import common
common.configure_models()
print('LLM says:', common.Settings.llm.complete('Say hello in five words or fewer.').text)
print('Handbook is', len(common.load_handbook_text()), 'characters')
"
```

Expected output (LLM wording will vary; the character count won't):

```
LLM says: Hello from me to you!
Handbook is 5028 characters
```

If this fails, fix it here — every script from this point on assumes `common.py` already works.

## Checkpoint

<details>
<summary>Full <code>common.py</code></summary>

```python
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
```

</details>

This matches [../rag-with-llamaindex-and-chunking/common.py](../rag-with-llamaindex-and-chunking/common.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'common'` in a later script | Running a script from the wrong directory | Run every `uv run <script>.py` from inside `rag-with-llamaindex-and-chunking/`, so `common.py` is a sibling importable module |
| `httpx.ConnectError` from the smoke test | Ollama isn't running or the wrong port | Confirm `curl http://localhost:11434` responds |
| `chromadb.errors...` when a later script calls `get_chroma_collection` | Chroma container isn't running | `docker compose up -d`, then `curl http://localhost:8000/api/v2/heartbeat` |
| Smoke test's character count is very different from 3372 | `data/employee_handbook.md` wasn't saved completely, or has different line endings | Re-save the file from Step 1, checking it has all six `##` sections |

Next: **[Fixed-Size Chunking](04-fixed-size-chunking.md)** — write the first (and simplest) of the six strategies.
