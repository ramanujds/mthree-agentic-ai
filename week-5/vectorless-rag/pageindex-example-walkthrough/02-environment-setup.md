# Step 1 — Environment Setup

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Building the Tree](03-building-the-tree.md)

## Goal

Get Ollama running, scaffold the project, and write the sample document this app will navigate — before writing any application code.

## Why this matters

This app talks to exactly one external service over HTTP: Ollama. If it isn't up, every later step fails with a connection error that has nothing to do with the code you're writing. Getting it running and verified *first* means every failure from here on is actually about the code.

It's also worth noticing what's **not** here: no vector database to start, no second model to pull for embeddings, no Docker Compose file. That absence is the whole point of this app, not an oversight — see [../pageindex-example/README.md](../pageindex-example/README.md#benefit-over-the-llamaindex-example) for the full comparison against a vector-store-backed pipeline.

## 1. Install and start Ollama

If you don't already have [Ollama](https://ollama.com) installed, install it and start it (the desktop app, `ollama serve`, or Ollama's own Docker image all work — this walkthrough just needs `http://localhost:11434` to respond).

Pull the one model this app uses:

```bash
ollama pull llama3:8b
```

Verify Ollama is reachable:

```bash
curl http://localhost:11434
```

You should get back `Ollama is running`.

## 2. Scaffold the Python project

```bash
mkdir pageindex-example && cd pageindex-example
uv init --no-workdir --python 3.13 .
```

Notice there's no `uv add` step here. This app has **zero third-party dependencies** — everything it needs (`re`, `dataclasses`, `itertools`, `json`, `urllib.request`) ships with Python itself. Open the generated `pyproject.toml` and confirm `dependencies = []`.

## 3. Write the sample handbook

```bash
mkdir data
```

`data/company_handbook.md` — a small document with real hierarchy (an H1, several H2 sections, H3 sub-sections under Onboarding) and one deliberate cross-reference from Remote Work Policy to Appendix A:

```markdown
# Company Handbook

## Remote Work Policy

Employees may work remotely up to 3 days per week, subject to manager
approval. Requests must be submitted at least 2 business days in advance
through the HR portal. For team-specific exceptions, see Appendix A.

## Vacation Policy

All full-time employees accrue 18 days of paid vacation per year. Unused
vacation days can be carried over to the next year, up to a maximum of 5
days. Vacation requests must be submitted at least 1 week in advance.

## Expense Reimbursement

Employees can be reimbursed for business-related expenses such as travel,
client meals, and conference fees. Receipts must be submitted within 30
days of the expense. Reimbursements are processed within 10 business days
of approval.

## Onboarding

### Getting a laptop

New hires receive a laptop on their first day, shipped by the IT
department. If it hasn't arrived by day 2, contact it-support@example.com.

### Setting up email

Your email account is created automatically before your start date.
Check your personal email for a welcome message with setup instructions.

### Point of contact

Your assigned onboarding buddy will reach out on your first day. If you
haven't heard from them by 10am, contact your manager directly.

### Internal tool access

Access to Slack, the HR portal, and internal wikis is granted within
the first 24 hours of your start date.

## Appendix A: Team Exceptions

Sales team members may work remotely up to 5 days per week during Q4 to
support year-end client travel, with manager approval.

Engineers on the on-call rotation may work remotely full-time during
their on-call week, regardless of the standard 3-day limit.
```

Keep this file in mind as you build — every later step's "Try it" output is checkable against what's actually in it.

## 4. Scaffold `main.py`

Start with the docstring, one import, and config constants only — no logic yet.

```python
"""
PageIndex-style vectorless RAG example.

No vector database, no embeddings, no RAG framework: the document is parsed
into a hierarchical tree (title + LLM summary + text per section), and the
LLM navigates that tree directly -- descending one heading level at a time,
then following any "see Appendix X" cross-reference -- instead of a
similarity search over chunks. Only stdlib + a local Ollama endpoint.
"""

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "company_handbook.md")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

Reading configuration from environment variables with hardcoded fallbacks means this same file works untouched whether you're pointing at a local Ollama, a remote one, or a different model tag — override with an env var instead of editing code.

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
PageIndex-style vectorless RAG example.

No vector database, no embeddings, no RAG framework: the document is parsed
into a hierarchical tree (title + LLM summary + text per section), and the
LLM navigates that tree directly -- descending one heading level at a time,
then following any "see Appendix X" cross-reference -- instead of a
similarity search over chunks. Only stdlib + a local Ollama endpoint.
"""

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "company_handbook.md")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curl http://localhost:11434` connection refused | Ollama isn't running | Start the Ollama desktop app or run `ollama serve` |
| `ModuleNotFoundError` later on | Ran with `python` instead of `uv run` | Use `uv run main.py` — no dependencies to install, but `uv run` still uses the project's own Python |
| First real LLM call later on is very slow | Normal — Ollama loads the model into memory on first use | Subsequent calls in the same session are much faster |

Next: **[Building the Tree](03-building-the-tree.md)** — turn `company_handbook.md`'s headings into a navigable tree.
