# Step 4 — Recursive / Sentence-Aware Chunking

> [Back to index](README.md) · Previous: [Fixed-Size Chunking](04-fixed-size-chunking.md) · Next: [Sentence-Window Chunking](06-sentence-window-chunking.md)

## Goal

Build `02_sentence_splitter.py`: swap `TokenTextSplitter` for `SentenceSplitter`, and compare its chunk boundaries directly against Step 3's.

## Why this matters

`SentenceSplitter` is LlamaIndex's default chunker, and the reason is exactly what you saw go wrong in Step 3: it tries paragraph breaks first, then sentence breaks, and only falls back to a hard character cut if a chunk genuinely still doesn't fit within `chunk_size`. It is still just approximating "where a chunk should end" by a token budget — it has no idea what the text *means* — but it refuses to cut inside a sentence when a nearby boundary is available.

This is the "recursive splitting" strategy from [../vector-dbs/chunking.md, section 2](../vector-dbs/chunking.md): a prioritized list of separators, falling through to a harder cut only when necessary. It's the right default for most prose, which is why it's worth building right after the naive version — you now have a direct, same-document, same-question comparison to point at.

## 1. Swap the splitter

Copy `01_fixed_size_chunking.py` to `02_sentence_splitter.py` and change three things: the import, the splitter construction, and the collection name (so it doesn't share Step 3's Chroma collection).

```python
"""
02 - Recursive / sentence-aware chunking (SentenceSplitter)

LlamaIndex's default splitter: tries to break on paragraph boundaries
first, then sentences, only falling back to a hard cut if a chunk still
doesn't fit -- the "recursive splitting" strategy. Compare the chunk
boundaries here against 01_fixed_size_chunking.py's output for the same
document. See ../vector-dbs/chunking.md, section 2.

Run:
    uv run 02_sentence_splitter.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_sentence_splitter"


def main():
    configure_models()

    splitter = SentenceSplitter(chunk_size=120, chunk_overlap=20)
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Recursive/sentence-aware chunking (SentenceSplitter, chunk_size=120 tokens)")
```

Same `chunk_size` and `chunk_overlap` as Step 3, deliberately — the only variable changing is the splitter class, so any difference in the output is attributable to that one change.

## Try it

```bash
uv run 02_sentence_splitter.py
```

Expected output (compare directly against Step 3's chunk `[1]`):

```
=== Recursive/sentence-aware chunking (SentenceSplitter, chunk_size=120 tokens): 10 chunk(s) ===
[0] (530 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
[1] (447 chars) Employees on a performance improvement plan are required to work on-site for the duration of the plan, regardless of their normal remote work arrangement.  Equi...
[2] (532 chars) Unused vacation days can be carried over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at year-end unless local l...
```

Every chunk here starts at the beginning of a sentence. Chunk `[1]` starts with "Employees on a performance..." — a full sentence — instead of Step 3's "doing so." mid-sentence fragment. Same document, same `chunk_size`, same `chunk_overlap`: the only thing that changed is that this splitter *looks for* a sentence boundary near the size limit instead of counting blindly.

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

Identical to Step 3's ingestion and query code — only `COLLECTION_NAME` differs, which is exactly the point: from here on, the only thing that should change between scripts is the chunking step itself.

## Try it (full run)

```bash
uv run 02_sentence_splitter.py
```

Expected output (LLM wording will vary):

```
Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: Client meal reimbursements are capped at $75 per person, and alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

  source (0.638): Reimbursements are processed within 10 business days of approval and are paid out via direct deposit...
  source (0.485): Part-time employees accrue vacation on a pro-rated basis according to their contracted hours. Employ...
------------------------------------------------------------
Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: All full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days. Unused vacation days can be carried over to the next year, up to a maximum of 5 days.

  source (0.722): Unused vacation days can be carried over to the next year, up to a maximum of 5 days; any unused bal...
  source (0.664): Employees on a performance improvement plan are required to work on-site for the duration of the pla...
------------------------------------------------------------
```

Both strategies answered these two questions correctly in this document — the mid-sentence cuts in Step 3 happened not to separate a fact from its context this time. That's worth sitting with: fixed-size chunking's boundary problem is a *risk*, not a guaranteed failure on every query. It's the kind of bug that passes testing on your two sample questions and then fails in production on the third one nobody tried.

## Checkpoint

<details>
<summary>Full <code>02_sentence_splitter.py</code></summary>

```python
"""
02 - Recursive / sentence-aware chunking (SentenceSplitter)

LlamaIndex's default splitter: tries to break on paragraph boundaries
first, then sentences, only falling back to a hard cut if a chunk still
doesn't fit -- the "recursive splitting" strategy. Compare the chunk
boundaries here against 01_fixed_size_chunking.py's output for the same
document. See ../vector-dbs/chunking.md, section 2.

Run:
    uv run 02_sentence_splitter.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_sentence_splitter"


def main():
    configure_models()

    splitter = SentenceSplitter(chunk_size=120, chunk_overlap=20)
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Recursive/sentence-aware chunking (SentenceSplitter, chunk_size=120 tokens)")

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

This matches [../rag-with-llamaindex-and-chunking/02_sentence_splitter.py](../rag-with-llamaindex-and-chunking/02_sentence_splitter.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Chunks look identical to Step 3's | Forgot to change the import from `TokenTextSplitter` to `SentenceSplitter` | Double-check the `node_parser` import and the splitter construction line |
| `chunking_sentence_splitter` collection has 0 vectors after a run | Chroma isn't running, or `chroma_collection.count()` raised before reaching the ingest branch | `curl http://localhost:8000/api/v2/heartbeat`; re-run with the container up |
| Confusing this script's output with Step 3's in the terminal | Ran both scripts back-to-back without noting which is which | Each `print_nodes` call includes the strategy name in its label — check that line before comparing |

Next: **[Sentence-Window Chunking](06-sentence-window-chunking.md)** — go smaller still: one sentence per embedded chunk, with a wider window kept in reserve.
