# Step 1 — Environment Setup

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Configure Ollama Settings](03-configure-ollama-settings.md)

## Goal

Get every external piece running before writing application code: Ollama serving both an LLM and an embedding model, and a Chroma server running in Docker. Scaffold the project so it's ready to grow.

## Why this matters

This app talks to two separate local services over HTTP — Ollama and Chroma — plus reads local files. If either service isn't up, every later step fails with a connection error that has nothing to do with the code you're writing. Getting both running and verified *first* means every failure from here on is actually about the code, not the environment.

It's also worth noticing something: **Ollama serves two different jobs from two different models.** `llama3:8b` generates text (the LLM); `nomic-embed-text` turns text into vectors (the embedding model). They're unrelated capabilities that happen to share the same local server and API shape — don't assume one model can do both jobs.

## 1. Install and start Ollama

If you don't already have [Ollama](https://ollama.com) installed, install it and start it (the desktop app, `ollama serve`, or Ollama's own Docker image all work — this walkthrough just needs `http://localhost:11434` to respond).

Pull the two models this app uses:

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

Verify Ollama is reachable:

```bash
curl http://localhost:11434
```

You should get back `Ollama is running`.

## 2. Start Chroma via Docker

Create the project folder and a `docker-compose.yml` that runs Chroma in client-server mode, persisting to a named volume:

```bash
mkdir simple-rag-example-chromadb && cd simple-rag-example-chromadb
```

```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    container_name: simple-rag-chromadb
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/data
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

volumes:
  chroma_data:
```

`IS_PERSISTENT=TRUE` tells Chroma to write to the `/data` path (backed by the `chroma_data` volume) instead of keeping everything in memory — without it, restarting the container would lose all vectors, defeating the entire point of this walkthrough.

Start it:

```bash
docker compose up -d
```

Verify it's up:

```bash
curl http://localhost:8000/api/v2/heartbeat
```

You should get a JSON response with a timestamp, not a connection error.

## 3. Scaffold the Python project

```bash
uv init --no-workdir --python 3.13 .
```

Replace the generated `pyproject.toml` dependencies (or use `uv add`) so it declares what this app needs:

```bash
uv add "chromadb>=0.5.0" "llama-index-core>=0.14.24" "llama-index-embeddings-ollama>=0.10.0" "llama-index-llms-ollama>=0.11.0" "llama-index-vector-stores-chroma>=0.4.0"
```

Create the sample data the app will answer questions about:

```bash
mkdir data
```

`data/company_policy.txt`:

```text
Remote Work Policy

Employees may work remotely up to 3 days per week, subject to manager
approval. Requests must be submitted at least 2 business days in advance
through the HR portal.

Vacation Policy

All full-time employees accrue 18 days of paid vacation per year. Unused
vacation days can be carried over to the next year, up to a maximum of 5
days. Vacation requests must be submitted at least 1 week in advance.

Expense Reimbursement

Employees can be reimbursed for business-related expenses such as travel,
client meals, and conference fees. Receipts must be submitted within 30
days of the expense. Reimbursements are processed within 10 business days
of approval.
```

`data/onboarding_faq.txt`:

```text
Onboarding FAQ

Q: How do I get a laptop?
A: New hires receive a laptop on their first day, shipped by the IT
department. If it hasn't arrived by day 2, contact it-support@example.com.

Q: How do I set up my email?
A: Your email account is created automatically before your start date.
Check your personal email for a welcome message with setup instructions.

Q: Who is my point of contact during onboarding?
A: Your assigned onboarding buddy will reach out on your first day. If you
haven't heard from them by 10am, contact your manager directly.

Q: When do I get access to internal tools?
A: Access to Slack, the HR portal, and internal wikis is granted within
the first 24 hours of your start date.
```

## 4. Scaffold `main.py`

Start with the docstring, imports, and config constants only — no logic yet. Every constant is read from an environment variable with a sane local default, so nothing here is hardcoded for one machine.

```python
"""
RAG example with LlamaIndex + Chroma DB.

Chroma runs as a separate server (via `docker compose up`) and persists
vectors to disk, unlike the in-memory VectorStoreIndex in the plain
simple-rag-example. Both the embedding model and the LLM run locally
through Ollama, so no API key is needed.
"""

import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

Reading configuration from environment variables with hardcoded fallbacks means this same file works untouched whether you're pointing at a local Ollama, a remote one, or a different model tag — you override with an env var instead of editing code.

## Try it

```bash
uv run main.py
```

Expected output:

```
Scaffold ready.
```

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

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curl: (7) Failed to connect` on port 8000 | Chroma container isn't running | `docker compose up -d`, then `docker compose ps` to confirm it's `Up` |
| `curl http://localhost:11434` connection refused | Ollama isn't running | Start the Ollama desktop app or run `ollama serve` |
| `docker compose up` succeeds but `heartbeat` fails after a restart | Forgot `IS_PERSISTENT=TRUE`, or volume was removed | Check the `environment:` block and that `chroma_data` volume still exists (`docker volume ls`) |
| `ModuleNotFoundError` later on | Ran with `python` instead of `uv run`, or a dependency wasn't added | Use `uv run main.py`; confirm the package is listed under `dependencies` in `pyproject.toml` |

Next: **[Configure Ollama Settings](03-configure-ollama-settings.md)** — now that both services are reachable, wire LlamaIndex up to Ollama.
