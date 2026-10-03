# Step 3 — Ingest: Chunking and Schema

> [Back to index](README.md) · Previous: [Connections and Config](03-connections-config.md) · Next: [Ingest: Extraction and Write](05-ingest-extraction-and-write.md)

## Goal

Start `ingest.py`: read the sample file, split it into chunks, and declare the schema (which node types and relationship types the graph is allowed to contain). No LLM call and no database write yet.

## Why this matters

Two decisions made here determine how good the whole graph is.

**Chunking.** The LLM will read one chunk at a time and extract entities and relations from it. Chunks that are too large make extraction sloppy and expensive; chunks that are too small cut a sentence off from the context that gives it meaning ("It is controlled by Bob Petrov" is useless if "It" ended up in the previous chunk). `RecursiveCharacterTextSplitter` tries paragraph breaks first, then sentences, then words, so it prefers to cut at natural boundaries. `chunk_overlap=50` repeats a little text at each boundary so a fact straddling the cut survives in at least one chunk.

**Schema.** If you let the LLM invent any node label and relationship name it likes, you get `OWNS`, `OWNED_BY`, `HAS_OWNER`, `OWNERSHIP` all describing the same thing, and queries can never match them reliably. Constraining the extractor to a fixed list gives the graph a consistent vocabulary. Each relationship is a `(source label, type, target label)` triple, which also fixes direction: `OWNED_BY` goes from the owned company to the owner, never the other way. The Cypher the LLM writes later in `query.py` leans on exactly this consistency.

## 1. Scaffold the file with imports

Create `ingest.py`:

```python
"""Step 1: text -> chunks -> LLM extracts entities/relations -> Neo4j."""
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

The docstring's `Step 1` means phase 1 of the app (see [../notes/WORKFLOW.md](../notes/WORKFLOW.md)), not this walkthrough's numbering.

## 2. Declare the schema

Add below the imports:

```python
# Constrain the schema so the LLM produces a clean, consistent graph.
ALLOWED_NODES = ["Person", "Company", "SanctionList", "Loan", "Bank"]
ALLOWED_RELATIONSHIPS = [
    ("Company", "OWNED_BY", "Company"),
    ("Company", "OWNED_BY", "Person"),
    ("Company", "CONTROLLED_BY", "Person"),
    ("Person", "DIRECTOR_OF", "Company"),
    ("Person", "ON_LIST", "SanctionList"),
    ("Company", "HAS_LOAN_WITH", "Bank"),
    ("Company", "MANAGED_BY", "Person"),
]
```

`OWNED_BY` appears twice because a company can be owned by another company (Acme by Zenith) or by a person (Globex by Priya). Every relationship in the sample text maps to one of these seven triples, which is what makes the schema tight enough to be useful without being so narrow that it drops facts.

## 3. Load and chunk the file

Add the function:

```python
def ingest(path: str = "data/sample_docs.txt") -> None:
    text = Path(path).read_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=c, metadata={"source": path}) for c in splitter.split_text(text)]
    print(f"Split {path} into {len(docs)} chunks")
```

Each chunk is wrapped in a LangChain `Document` with a `source` metadata field. Later, `include_source=True` uses these documents to link every graph node back to the chunk it came from, which is what makes a graph answer traceable to its original text.

## Try it

```bash
uv run python -c "from ingest import ingest; ingest()"
```

Expected output:

```
Split data/sample_docs.txt into 1 chunks
```

One chunk, not five. The whole sample file is 434 characters, and the splitter merges adjacent paragraphs until it hits the 500-character limit, so everything fits together. That is fine for a demo, but it is worth pausing on: with a real corpus of thousands of pages you would get thousands of chunks, and each one costs an LLM call in the next step.

## Checkpoint

<details>
<summary>Full <code>ingest.py</code> so far</summary>

```python
"""Step 1: text -> chunks -> LLM extracts entities/relations -> Neo4j."""
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Constrain the schema so the LLM produces a clean, consistent graph.
ALLOWED_NODES = ["Person", "Company", "SanctionList", "Loan", "Bank"]
ALLOWED_RELATIONSHIPS = [
    ("Company", "OWNED_BY", "Company"),
    ("Company", "OWNED_BY", "Person"),
    ("Company", "CONTROLLED_BY", "Person"),
    ("Person", "DIRECTOR_OF", "Company"),
    ("Person", "ON_LIST", "SanctionList"),
    ("Company", "HAS_LOAN_WITH", "Bank"),
    ("Company", "MANAGED_BY", "Person"),
]


def ingest(path: str = "data/sample_docs.txt") -> None:
    text = Path(path).read_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=c, metadata={"source": path}) for c in splitter.split_text(text)]
    print(f"Split {path} into {len(docs)} chunks")
```

</details>

This is an intermediate checkpoint; the file reaches its final form, matching [../app/ingest.py](../app/ingest.py), in Step 4.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `FileNotFoundError: data/sample_docs.txt` | Running from a different folder than the project root | `cd` into `kg-app` first; the default path is relative to where you run the command |
| `ModuleNotFoundError: langchain_core` | Dependencies not installed, or ran plain `python` | `uv sync`, then use `uv run` |
| Relationship direction later looks backwards in Neo4j | Triple written as `(owner, "OWNS", owned)` mentally but declared the other way | Re-read each triple as "source IS relationship TO target": `Company OWNED_BY Person` means the company points at its owner |
| Chunk count differs from the one above | Sample file edited (extra blank lines, different wording) | Compare against the exact text in [Step 1](02-environment-setup.md); the count depends on total length |

Next: **[Ingest: Extraction and Write](05-ingest-extraction-and-write.md)**.
