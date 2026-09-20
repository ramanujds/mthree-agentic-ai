# Step 8 — Structure-Aware Chunking

> [Back to index](README.md) · Previous: [Hierarchical / Parent-Child Chunking](08-hierarchical-parent-child-chunking.md) · Next: [Recap and Exercises](10-recap-and-exercises.md)

## Goal

Build `06_markdown_structure_aware.py`: use `MarkdownNodeParser` to cut one chunk per `##` section, using the document's own headers as the boundaries instead of any size or similarity calculation.

## Why this matters

Every prior strategy in this walkthrough approximated "where a chunk should end" — by token count, by sentence, by embedding similarity — because none of them actually knew anything about the document's own structure. But `data/employee_handbook.md` isn't unstructured prose: it's Markdown, with six clearly-marked `##` sections. When a document already tells you where its own topic boundaries are, using them directly is both simpler and more reliable than inferring them.

The catch, covered in [../vector-dbs/chunking.md, section 5](../vector-dbs/chunking.md), is that this strategy is only as good as the structure it depends on. It works beautifully here because every section in this handbook has a clean, consistent `##` header. It would work far worse on a scanned PDF, an inconsistently-formatted document, or plain text with no headers at all — there'd be nothing for this parser to key off of.

## 1. Parse by header and inspect the header metadata

```python
"""
06 - Structure-aware chunking (MarkdownNodeParser)

Splits along the document's own Markdown headers instead of a raw
character/token count, so each chunk lines up with a real section
("Remote Work Policy", "Vacation Policy", ...) and carries its header
path as metadata. Compare the chunk count/boundaries here against
01/02's token-count-driven splits. Only works well because our sample
document has clean, consistent Markdown headers -- see the pitfalls in
../vector-dbs/chunking.md, section 5.

Run:
    uv run 06_markdown_structure_aware.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_markdown_structure"


def main():
    configure_models()

    parser = MarkdownNodeParser()
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Structure-aware chunking (MarkdownNodeParser, one chunk per section)")

    # Each node carries its header path as metadata -- print it for the
    # first few nodes to show what structure-aware chunking gives you
    # for free that a size-based splitter doesn't.
    print("--- Header metadata per chunk ---")
    for i, node in enumerate(nodes):
        headers = {k: v for k, v in node.metadata.items() if k.startswith("header")}
        print(f"[{i}] {headers}")
    print()
```

`MarkdownNodeParser()` takes no size parameter at all — unlike every earlier splitter, there is nothing to tune here except which document you feed it. It attaches a `header_path` to each node's metadata, tracking which headers that chunk falls under — useful later for metadata filtering (see [../vector-dbs/chroma-db-filtering.md](../vector-dbs/chroma-db-filtering.md)) even though this script doesn't use it for filtering itself.

## Try it

```bash
uv run 06_markdown_structure_aware.py
```

Expected output:

```
=== Structure-aware chunking (MarkdownNodeParser, one chunk per section): 7 chunk(s) ===
[0] (29 chars) # Acme Corp Employee Handbook
[1] (821 chars) ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted at least 2 business days in ad...
[2] (773 chars) ## Vacation Policy  All full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days. Unused vacation days can be carried...
[3] (811 chars) ## Expense Reimbursement  Employees can be reimbursed for business-related expenses such as travel, client meals, and conference fees. Receipts must be submitte...
[4] (929 chars) ## Onboarding  New hires receive a laptop on their first day, shipped by the IT department to their home address or delivered to their desk for office-based rol...
[5] (802 chars) ## Code of Conduct  All employees are expected to treat colleagues, clients, and partners with professionalism and respect. Harassment, discrimination, or retal...
[6] (850 chars) ## IT Security Policy  All company devices must have disk encryption and endpoint security software enabled before they can connect to internal systems; IT enfo...

--- Header metadata per chunk ---
[0] {'header_path': '/'}
[1] {'header_path': '/Acme Corp Employee Handbook/'}
[2] {'header_path': '/Acme Corp Employee Handbook/'}
[3] {'header_path': '/Acme Corp Employee Handbook/'}
[4] {'header_path': '/Acme Corp Employee Handbook/'}
[5] {'header_path': '/Acme Corp Employee Handbook/'}
[6] {'header_path': '/Acme Corp Employee Handbook/'}
```

Seven chunks — one for the bare `# Acme Corp Employee Handbook` title line, and exactly one per `##` section after it. Compare this against every earlier strategy: Steps 3-4 produced 10 chunks that don't line up with sections at all, Step 6 produced 5 chunks that visibly straddle sections, Step 5 produced 21-26 nodes at three different granularities. This is the cleanest, most legible split of the six — a direct payoff of the document actually having the structure this parser depends on.

(`header_path` tracks *ancestor* headers, which is why every section shows `/Acme Corp Employee Handbook/` — the `#` title — rather than its own `##` heading; the section's own heading is part of the chunk's text content itself, visible at the start of each preview above.)

## 2. Ingest and query (unchanged pattern)

```python
    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    query_engine = index.as_query_engine(similarity_top_k=2)

    questions = [
        "What is the maximum client meal reimbursement per person, and what's the rule about alcohol?",
        "How many vacation days do employees accrue per year, and how many can be carried over?",
    ]
    for question in questions:
        response = query_engine.query(question)
        print_answer(question, response, response.source_nodes)


if __name__ == "__main__":
    main()
```

## Try it (full run)

```bash
uv run 06_markdown_structure_aware.py
```

Expected output (LLM wording will vary):

```
Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: Client meal reimbursements are capped at $75 per person, and alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

  source (0.557): ## Expense Reimbursement  Employees can be reimbursed for business-related expenses such as travel, ...
  source (0.431): ## Vacation Policy  All full-time employees accrue 18 days of paid vacation per year, accrued monthl...
------------------------------------------------------------
Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: Employees accrue 18 days of paid vacation per year, and they can carry over up to 5 days.
------------------------------------------------------------
```

Both correct, and each retrieved source is an entire, coherent policy section — the alcohol rule and the $75 cap it modifies are in the same chunk by construction, because they're in the same section.

## Checkpoint

<details>
<summary>Full <code>06_markdown_structure_aware.py</code></summary>

```python
"""
06 - Structure-aware chunking (MarkdownNodeParser)

Splits along the document's own Markdown headers instead of a raw
character/token count, so each chunk lines up with a real section
("Remote Work Policy", "Vacation Policy", ...) and carries its header
path as metadata. Compare the chunk count/boundaries here against
01/02's token-count-driven splits. Only works well because our sample
document has clean, consistent Markdown headers -- see the pitfalls in
../vector-dbs/chunking.md, section 5.

Run:
    uv run 06_markdown_structure_aware.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_markdown_structure"


def main():
    configure_models()

    parser = MarkdownNodeParser()
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Structure-aware chunking (MarkdownNodeParser, one chunk per section)")

    # Each node carries its header path as metadata -- print it for the
    # first few nodes to show what structure-aware chunking gives you
    # for free that a size-based splitter doesn't.
    print("--- Header metadata per chunk ---")
    for i, node in enumerate(nodes):
        headers = {k: v for k, v in node.metadata.items() if k.startswith("header")}
        print(f"[{i}] {headers}")
    print()

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    query_engine = index.as_query_engine(similarity_top_k=2)

    questions = [
        "What is the maximum client meal reimbursement per person, and what's the rule about alcohol?",
        "How many vacation days do employees accrue per year, and how many can be carried over?",
    ]
    for question in questions:
        response = query_engine.query(question)
        print_answer(question, response, response.source_nodes)


if __name__ == "__main__":
    main()
```

</details>

This matches [../rag-with-llamaindex-and-chunking/06_markdown_structure_aware.py](../rag-with-llamaindex-and-chunking/06_markdown_structure_aware.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Way more than 7 chunks | Source document has extra `#`/`##`/`###` headers you didn't expect (e.g., from a copy-paste artifact) | Check `data/employee_handbook.md` for stray heading markers |
| Only 1 giant chunk | Headers use `*Bold Text*` or another non-Markdown convention instead of real `#`/`##` syntax | `MarkdownNodeParser` only recognizes actual Markdown heading syntax |
| `header_path` empty or `/` for every node | Document has no headers above that node (e.g., text before the first heading) | Expected for content before any header — see chunk `[0]` above |
| Tempted to conclude "structure-aware chunking is always best" | This document was specifically written with clean headers to make this comparison work | Re-read this step's "Why this matters" — the strategy is only as good as the source structure |

Next: **[Recap and Exercises](10-recap-and-exercises.md)** — pull all six strategies together.
