# Step 2 — Configure Ollama Settings

> [Back to index](README.md) · Previous: [Environment Setup](02-environment-setup.md) · Next: [Connecting to Chroma](04-connecting-to-chroma.md)

## Goal

Wire LlamaIndex up to the two Ollama models — one for generation, one for embedding — and prove both work in isolation before adding Chroma or documents into the mix.

## Why this matters

LlamaIndex uses a global `Settings` object as the default LLM and embedding model for anything you build afterwards — `VectorStoreIndex`, query engines, retrievers all read from it unless told otherwise. Setting it once, early, means every component built later automatically uses the right models without having to be told explicitly each time.

Testing the connection here — before touching Chroma or the document loader — isolates the failure surface. If something's misconfigured (wrong model tag, wrong port, model not pulled), you want that error here, with one clear cause, rather than three steps from now buried under a Chroma connection or a document-loading traceback.

## 1. Import and configure `Settings`

```python
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
```

```python
def main():
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    print("Settings configured.")
```

`request_timeout=120.0` matters specifically for local models: the first call after Ollama (re)loads a model into memory can take much longer than a typical API timeout allows. 120 seconds gives it room without hanging forever on a genuine failure.

## 2. Smoke-test both models directly

Replace the `print("Settings configured.")` line with two direct calls — one to the LLM, one to the embedding model — so you can see each one working before anything else depends on them:

```python
    print("LLM says:", Settings.llm.complete("Say hello in five words or fewer.").text)

    vector = Settings.embed_model.get_text_embedding("test")
    print(f"Embedding has {len(vector)} numbers, e.g. {vector[:3]}...")
```

`Settings.llm.complete(...)` is the plainest possible LLM call — one string in, one string out, no chat history, no tools. `get_text_embedding(...)` is the plainest possible embedding call — one string in, one vector out. Neither of these calls appears in the finished app; they exist only so you can prove connectivity for each model independently.

## Try it

```bash
uv run main.py
```

Expected output (wording from the LLM will vary; the embedding length won't):

```
LLM says: Hello! Nice to meet you.
Embedding has 768 numbers, e.g. [0.0123, -0.0456, 0.0789]...
```

`nomic-embed-text` produces 768-dimensional vectors — if you swap in a different embedding model later, expect this number to change, and remember that a vector store built with one embedding model's output can't be searched with vectors from another (they're different-shaped and mean different things).

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

from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    print("LLM says:", Settings.llm.complete("Say hello in five words or fewer.").text)

    vector = Settings.embed_model.get_text_embedding("test")
    print(f"Embedding has {len(vector)} numbers, e.g. {vector[:3]}...")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `httpx.ConnectError` | Ollama isn't running, or `OLLAMA_BASE_URL` points at the wrong port | Confirm `curl http://localhost:11434` responds |
| `model 'llama3:8b' not found` | Model wasn't pulled | `ollama pull llama3:8b` (and `nomic-embed-text`) |
| Call hangs for a long time on first run | Model is loading into memory for the first time | Normal — subsequent calls are much faster |
| `AttributeError` on `Settings.llm` later in the app | `Settings.llm`/`Settings.embed_model` set inside a function that never ran, or set after the code that needed it | `Settings` is a global — order of assignment vs. use matters, same as any global |

Next: **[Connecting to Chroma](04-connecting-to-chroma.md)** — now that both models work, connect to the Chroma server that will store their output.
