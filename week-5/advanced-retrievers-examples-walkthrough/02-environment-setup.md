# Step 1 — Environment Setup

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Vector Index Retriever](03-vector-index-retriever.md)

## Goal

Get Ollama running, scaffold the uv project, and create the two shared HR documents that four of the six scripts will read from.

## Why this matters

Every script in this walkthrough talks to a local Ollama server for embeddings (and most also configure an LLM, even though several never actually call it). If Ollama isn't reachable, every later step fails with a connection error that has nothing to do with the retriever code you're about to write — so it's worth confirming that once, up front.

It's also worth deciding the data layout now: `data/company_policy.txt` and `data/onboarding_faq.txt` are shared by four of the six scripts (vector, BM25, document summary, fusion). The other two scripts — auto-merging and recursive — need their own, differently-shaped data (one long document, and a small citation graph of "papers"), which you'll create in their own steps instead of here. Putting *only* the shared files in `data/` now, and adding the rest later, is what makes the "always list `input_files=[...]` explicitly, never point a reader at the whole `data/` directory" rule in the next step actually matter — once `data/` accumulates files meant for other scripts, an unscoped reader would silently pull them all in.

## 1. Install Ollama and pull the models

If you haven't already, install and start [Ollama](https://ollama.com), then pull the two models this whole walkthrough uses:

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

Full instructions (desktop app vs. `ollama serve` vs. Docker) are in ["1. Install and start Ollama"](../simple-rag-example-chromadb-walkthrough/02-environment-setup.md) from the Chroma walkthrough — this walkthrough doesn't repeat them.

Verify Ollama is reachable:

```bash
curl http://localhost:11434
```

You should get back `Ollama is running`.

## 2. Scaffold the uv project

```bash
mkdir advanced-retrievers-examples && cd advanced-retrievers-examples
uv init --no-workdir --python 3.13 .
```

Add the dependencies every script in this walkthrough needs up front (Step 3 adds one more, later, when BM25 needs it):

```bash
uv add "llama-index-core>=0.14.24" "llama-index-embeddings-ollama>=0.10.0" "llama-index-llms-ollama>=0.11.0"
```

## 3. Create the shared sample data

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

These are two short HR-style documents, deliberately short — small enough that most of them fit into a single chunk. That's fine for the vector, BM25, and fusion steps; the document summary step (Step 4) is exactly where document-level, rather than chunk-level, granularity becomes the point.

## Try it

There's no Python file yet, so "trying it" means confirming the environment is actually ready:

```bash
uv sync
curl http://localhost:11434
ls data
```

Expected: `uv sync` completes with no errors, `curl` prints `Ollama is running`, and `ls data` shows `company_policy.txt` and `onboarding_faq.txt`.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curl: (7) Failed to connect` on port 11434 | Ollama isn't running | Start the Ollama desktop app or run `ollama serve` |
| First retrieval in a later step is very slow | Model not pulled yet, or being loaded into memory for the first time | `ollama pull llama3:8b` / `ollama pull nomic-embed-text`; subsequent calls are much faster |
| `ModuleNotFoundError` in a later step | Ran with `python` instead of `uv run`, or forgot `uv sync` after adding a dependency | Always use `uv run <script>.py`; re-run `uv sync` after any `uv add` |

Next: **[Vector Index Retriever](03-vector-index-retriever.md)** — the first, and simplest, of the six scripts.
