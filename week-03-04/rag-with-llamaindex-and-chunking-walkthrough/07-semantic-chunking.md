# Step 6 — Semantic Chunking

> [Back to index](README.md) · Previous: [Sentence-Window Chunking](06-sentence-window-chunking.md) · Next: [Hierarchical / Parent-Child Chunking](08-hierarchical-parent-child-chunking.md)

## Goal

Build `04_semantic_chunking.py`: use `SemanticSplitterNodeParser` to cut chunk boundaries wherever the embedding similarity between consecutive sentences drops, instead of at a fixed size.

## Why this matters

Every splitter so far has needed a `chunk_size` — a number you pick, disconnected from what the text is actually about. Semantic chunking asks a different question entirely: embed each sentence, look at how similar each sentence is to the next one, and cut a new chunk exactly where that similarity drops — i.e., where the *topic* changes. There is no `chunk_size` parameter here at all; boundaries are found, not chosen.

That power comes at a real cost, covered in [../vector-dbs/chunking.md, section 4](../vector-dbs/chunking.md): every sentence has to be embedded once just to decide where the boundaries go, on top of the embedding you'd do anyway for the final chunks. And the boundary you get depends on a `breakpoint_percentile_threshold` you still have to tune — it just moves the "number you have to pick" from a size in tokens to a percentile in a similarity distribution.

## 1. Build the splitter with its own embedding model instance

```python
"""
04 - Semantic chunking (SemanticSplitterNodeParser)

Embeds individual sentences, then cuts a new chunk boundary wherever the
similarity between consecutive sentences drops -- i.e. splits where the
*topic* actually changes, rather than at a fixed size. This costs an
extra embedding pass at ingestion time. See ../vector-dbs/chunking.md,
section 4.

Run:
    uv run 04_semantic_chunking.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    EMBED_MODEL,
    OLLAMA_BASE_URL,
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_semantic"


def main():
    configure_models()

    embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=90,
        embed_model=embed_model,
    )
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Semantic chunking (SemanticSplitterNodeParser, threshold=90th percentile)")
```

`SemanticSplitterNodeParser` takes its own `embed_model` argument directly, separately from `configure_models()`'s global `Settings.embed_model` — this walkthrough imports `EMBED_MODEL` and `OLLAMA_BASE_URL` from `common` to build one explicitly, so it's obvious which embedding calls belong to boundary-finding versus the later, final embedding of the chunks. `buffer_size=1` groups sentences one at a time when comparing similarity (a larger buffer compares small groups instead of single sentences); `breakpoint_percentile_threshold=90` means only the most significant 10% of similarity drops become chunk boundaries — lower it and you get more, smaller chunks; raise it and you get fewer, larger ones.

## Try it

```bash
uv run 04_semantic_chunking.py
```

Expected output:

```
=== Semantic chunking (SemanticSplitterNodeParser, threshold=90th percentile): 5 chunk(s) ===
[0] (219 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
[1] (1291 chars) Fully remote arrangements are only available to employees in roles explicitly designated as remote-eligible by their department head.  Managers may temporarily ...
[2] (1093 chars) Employees who leave the company are paid out for any unused, accrued vacation days as part of their final paycheck.  ## Expense Reimbursement  Employees can be ...
[3] (890 chars) If the laptop hasn't arrived by day 2, the new hire should contact it-support@example.com immediately so a loaner can be issued.  A new hire's email account is ...
[4] (1530 chars) Harassment, discrimination, or retaliation of any kind will not be tolerated and should be reported immediately to HR or through the anonymous ethics hotline.  ...
```

Only 5 chunks — far fewer than the 10 from Steps 3-4 or the 35 from Step 5, and much larger. Look at chunk `[1]`: it starts with "Fully remote arrangements..." (still Remote Work Policy) and, per its length, keeps going well past that section — this parser doesn't know or care that `## Vacation Policy` is a header; it only knows the sentence-to-sentence similarity never dropped enough to justify a cut there at the 90th-percentile threshold you chose. Chunk `[2]` explicitly straddles the end of Vacation Policy and the start of Expense Reimbursement in its preview text. Compare this against Step 8, where `MarkdownNodeParser` will cut at every `##` header regardless of topic similarity.

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
uv run 04_semantic_chunking.py
```

Expected output (LLM wording will vary):

```
Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: Client meal reimbursements are capped at $75 per person, and alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

  source (0.530): Employees who leave the company are paid out for any unused, accrued vacation days as part of their ...
  source (0.426): Fully remote arrangements are only available to employees in roles explicitly designated as remote-e...
------------------------------------------------------------
Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: Employees accrue 18 days of paid vacation per year, and they can carry over up to a maximum of 5 unused days to the next year.
------------------------------------------------------------
```

Both correct — the large, topic-clustered chunks here happen to keep each answer's supporting facts together in one chunk, at the cost of each chunk covering (and diluting the embedding across) more ground than a strictly single-topic chunk would.

## Checkpoint

<details>
<summary>Full <code>04_semantic_chunking.py</code></summary>

```python
"""
04 - Semantic chunking (SemanticSplitterNodeParser)

Embeds individual sentences, then cuts a new chunk boundary wherever the
similarity between consecutive sentences drops -- i.e. splits where the
*topic* actually changes, rather than at a fixed size. This costs an
extra embedding pass at ingestion time. See ../vector-dbs/chunking.md,
section 4.

Run:
    uv run 04_semantic_chunking.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    EMBED_MODEL,
    OLLAMA_BASE_URL,
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_semantic"


def main():
    configure_models()

    embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=90,
        embed_model=embed_model,
    )
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Semantic chunking (SemanticSplitterNodeParser, threshold=90th percentile)")

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

This matches [../rag-with-llamaindex-and-chunking/04_semantic_chunking.py](../rag-with-llamaindex-and-chunking/04_semantic_chunking.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Only 1 chunk produced | `breakpoint_percentile_threshold` too high (close to 100), so almost no similarity drop qualifies as a boundary | Lower the threshold, e.g. to 80 or 75 |
| Chunk count close to the sentence count | `breakpoint_percentile_threshold` too low, so nearly every sentence-to-sentence drop counts as a boundary | Raise the threshold back up |
| Ingestion noticeably slower than Steps 3/4 | Expected — every sentence gets embedded once to find boundaries, then again as part of building the final chunks | Not a bug; this is the ingestion-cost trade-off described in the chunking notes |
| `embed_model` passed to `SemanticSplitterNodeParser` seems redundant with `configure_models()` | It genuinely is a separate instance — `configure_models()` sets `Settings.embed_model` globally, but this parser also accepts one directly | Both point at the same Ollama model here; they don't have to in general |

Next: **[Hierarchical / Parent-Child Chunking](08-hierarchical-parent-child-chunking.md)** — search small chunks, but let the retriever hand back a bigger one when it's confident.
