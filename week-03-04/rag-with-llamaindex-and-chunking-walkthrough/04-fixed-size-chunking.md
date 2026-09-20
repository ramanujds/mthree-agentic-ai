# Step 3 — Fixed-Size Chunking

> [Back to index](README.md) · Previous: [Shared Scaffolding](03-shared-scaffolding.md) · Next: [Recursive / Sentence-Aware Chunking](05-sentence-aware-chunking.md)

## Goal

Build `01_fixed_size_chunking.py`: split the handbook into fixed-size token windows with `TokenTextSplitter`, and see exactly where that cuts across sentence boundaries.

## Why this matters

`TokenTextSplitter` is the simplest possible chunker: count tokens, cut every N of them (with some overlap), and repeat. It has no concept of a sentence, a paragraph, or a heading — it just counts. That makes it fast and completely predictable, but it also means a chunk boundary can land in the middle of a sentence, or even split a fact from the clause that gives it meaning (a number separated from what it's measuring).

This script also establishes the pattern every remaining script in this walkthrough follows: parse into nodes, print them, ingest-if-empty into a dedicated Chroma collection, build a query engine, ask the same two questions. Once this one works, the later scripts are almost entirely about swapping out the parser — everything else stays the same shape.

## 1. Imports and the chunking step

```python
"""
01 - Fixed-size chunking (TokenTextSplitter)

Splits the document into fixed-size token windows with overlap, with no
regard for sentence or paragraph boundaries. Fast and simple, but chunks
can cut mid-sentence or straddle two unrelated topics -- see
../vector-dbs/chunking.md, section 1 ("Fixed-Size Chunking").

Run:
    uv run 01_fixed_size_chunking.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_fixed_size"


def main():
    configure_models()

    splitter = TokenTextSplitter(chunk_size=120, chunk_overlap=20)
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Fixed-size chunking (TokenTextSplitter, chunk_size=120 tokens)")


if __name__ == "__main__":
    main()
```

`chunk_size=120` is a token count, not a character count — it's small on purpose here so the handbook (which is short) still produces enough chunks to show boundary effects. `chunk_overlap=20` means each chunk repeats the last 20 tokens of the previous one, which is the usual mitigation for splitting a sentence across a boundary — as you're about to see, it only partially helps.

## Try it

```bash
uv run 01_fixed_size_chunking.py
```

Expected output (truncated to the first few chunks):

```
=== Fixed-size chunking (TokenTextSplitter, chunk_size=120 tokens): 10 chunk(s) ===
[0] (627 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
[1] (574 chars) doing so. Employees on a performance improvement plan are required to work on-site for the duration of the plan, regardless of their normal remote work arrangem...
[2] (587 chars) over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at year-end unless local l...
```

Look closely at chunk `[1]`: it starts mid-sentence, with `doing so.` — the back half of a sentence that began in chunk `[0]` ("...must give at least 5 business days' notice before doing so."). That's not a bug in the code; it's exactly what a chunker with no sentence awareness does when a chunk-size boundary happens to fall inside a sentence.

## 2. Ingest into Chroma and query

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
```

This ingestion branch is the exact pattern from [simple-rag-example-chromadb's Step 6](../rag-with-LlamaIndex/simple-rag-example-chromadb-walkthrough/07-persistence-and-reuse.md): skip re-ingesting if `COLLECTION_NAME`'s collection already has vectors, otherwise embed `nodes` (not raw documents — the nodes you already built above) and store them. Every remaining script in this walkthrough reuses this exact branch unchanged; only the collection name and the `nodes` passed into it differ.

## Try it (again, full run)

```bash
uv run 01_fixed_size_chunking.py
```

Expected output (LLM wording will vary; the chunk count and boundaries will not):

```
Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: The maximum client meal reimbursement per person is $75. Additionally, alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

  source (0.567): out via direct deposit on the next regular payroll cycle. Client meal reimbursements are capped at $...
  source (0.544): contracted hours. Employees who leave the company are paid out for any unused, accrued vacation days...
------------------------------------------------------------
Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: All full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days. Unused vacation days can be carried over to the next year, up to a maximum of 5 days.

  source (0.715): over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at...
  source (0.704): doing so. Employees on a performance improvement plan are required to work on-site for the duration ...
------------------------------------------------------------
```

Both answers happen to come out correct here, despite the mid-sentence cuts — the facts needed weren't split across a boundary this time. Keep this run's output in mind for the next step, where `SentenceSplitter` never produces a chunk like `[1]` above in the first place.

## Checkpoint

<details>
<summary>Full <code>01_fixed_size_chunking.py</code></summary>

```python
"""
01 - Fixed-size chunking (TokenTextSplitter)

Splits the document into fixed-size token windows with overlap, with no
regard for sentence or paragraph boundaries. Fast and simple, but chunks
can cut mid-sentence or straddle two unrelated topics -- see
../vector-dbs/chunking.md, section 1 ("Fixed-Size Chunking").

Run:
    uv run 01_fixed_size_chunking.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_fixed_size"


def main():
    configure_models()

    splitter = TokenTextSplitter(chunk_size=120, chunk_overlap=20)
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Fixed-size chunking (TokenTextSplitter, chunk_size=120 tokens)")

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

This matches [../rag-with-llamaindex-and-chunking/01_fixed_size_chunking.py](../rag-with-llamaindex-and-chunking/01_fixed_size_chunking.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Chunk count changes between runs | `docker compose down -v` was run between them, resetting the collection, and the underlying text or splitter settings changed | Expected if you edited `chunk_size`; otherwise reset with `docker compose down -v && docker compose up -d` for a clean comparison |
| `get_nodes_from_documents` returns 1 giant node | `chunk_size` set far larger than the document's token count | Lower `chunk_size`, or accept that a short document may not need chunking at all |
| Second run doesn't reflect an edited `data/employee_handbook.md` | The collection already has vectors, so ingestion is skipped by design (same as every other Chroma example in this repo) | `docker compose down -v && docker compose up -d` to force re-ingestion |
| `AttributeError` on `response.source_nodes` | Called `print_answer` before `query_engine.query(...)`, or passed the wrong variable | Check `response = query_engine.query(question)` runs before `print_answer` |

Next: **[Recursive / Sentence-Aware Chunking](05-sentence-aware-chunking.md)** — the same document, but a splitter that respects sentence boundaries.
