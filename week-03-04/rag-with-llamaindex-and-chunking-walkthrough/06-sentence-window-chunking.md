# Step 5 — Sentence-Window Chunking

> [Back to index](README.md) · Previous: [Recursive / Sentence-Aware Chunking](05-sentence-aware-chunking.md) · Next: [Semantic Chunking](07-semantic-chunking.md)

## Goal

Build `03_sentence_window.py`: parse the handbook into one node per sentence with `SentenceWindowNodeParser`, and use `MetadataReplacementPostProcessor` to swap the matched sentence for a wider window of context at query time.

## Why this matters

Steps 3 and 4 both picked one `chunk_size` and lived with the trade-off it implies: bigger chunks give the LLM more context but dilute the embedding (a long chunk about several things matches queries about any one of them only loosely); smaller chunks embed more precisely but risk not containing enough surrounding text to actually answer the question.

Sentence-window chunking is a way to stop choosing: embed the *smallest* possible unit — a single sentence — so retrieval matching is as precise as it can be, but store a wider window of neighboring sentences in that node's metadata. When a query matches the single sentence, a **postprocessor** swaps in the window before the LLM ever sees it. You get precise retrieval and generous context, at the cost of maintaining that separate metadata field and choosing a window size.

This is the sentence-granularity version of the parent-child idea covered more generally in [../vector-dbs/chunking.md, section 7](../vector-dbs/chunking.md) — you'll build the full hierarchical version of that same idea in Step 7.

## 1. Parse into single-sentence nodes with a window

```python
"""
03 - Sentence-window chunking (SentenceWindowNodeParser)

Each node is a SINGLE sentence -- giving very precise embedding matches
-- but every node's metadata also stores a "window" of the surrounding
sentences. At query time, MetadataReplacementPostProcessor swaps the
matched single sentence back out for its window, so the LLM sees enough
context to actually answer. This is a sentence-granularity form of
parent-child chunking. See ../vector-dbs/chunking.md, section 3 and 7.

Run:
    uv run 03_sentence_window.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_sentence_window"


def main():
    configure_models()

    parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_sentence",
    )
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Sentence-window chunking (1 sentence per node, window=3)")
```

`window_size=3` means each node's metadata stores up to 3 sentences on either side of it. `window_metadata_key` and `original_text_metadata_key` name the two metadata fields this parser writes: the wider window, and the original single sentence (kept in case you need it back). Notice this parser has no `chunk_size` at all — the "chunk" *is* one sentence, always; only the window is configurable.

## Try it

```bash
uv run 03_sentence_window.py
```

Expected output (35 chunks — one per sentence in the handbook, far more than Steps 3/4's 10):

```
=== Sentence-window chunking (1 sentence per node, window=3): 35 chunk(s) ===
[0] (133 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval.
[1] (85 chars) Requests must be submitted at least 2 business days in advance through the HR portal.
[2] (133 chars) Fully remote arrangements are only available to employees in roles explicitly designated as remote-eligible by their department head.
```

Every node is a single sentence — the shortest chunks of any strategy in this walkthrough.

## 2. Prove the embedded text and the window actually differ

Add a small block right after the `print_nodes` call, before touching Chroma:

```python
    # Show that each node's embedded text (1 sentence) differs from the
    # wider window stored in its metadata -- that gap is the whole point.
    sample = nodes[5]
    print("--- Example: embedded sentence vs. stored window ---")
    print(f"Embedded (matched against queries): {sample.get_content()!r}")
    print(f"Window (sent to the LLM instead):   {sample.metadata['window']!r}\n")
```

## Try it

```bash
uv run 03_sentence_window.py
```

```
--- Example: embedded sentence vs. stored window ---
Embedded (matched against queries): 'Equipment for remote work, such as monitors and ergonomic chairs, can be requested through the Facilities portal and is subject to a $500 annual budget per employee.\n\n'
Window (sent to the LLM instead):   "Fully remote arrangements are only available to employees in roles explicitly designated as remote-eligible by their department head.\n\n Managers may temporarily suspend remote work privileges for a team during periods of critical project delivery, but must give at least 5 business days' notice before doing so.  Employees on a performance improvement plan are required to work on-site for the duration of the plan, regardless of their normal remote work arrangement.\n\n Equipment for remote work, such as monitors and ergonomic chairs, can be requested through the Facilities portal and is subject to a $500 annual budget per employee.\n\n ## Vacation Policy\n\nAll full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days.  Unused vacation days can be carried over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at year-end unless local law requires otherwise.\n\n Vacation requests must be submitted at least 1 week in advance through the HR portal and require manager approval. "
```

`sample.get_content()` — the text that actually gets embedded and matched against queries — is one sentence. `sample.metadata["window"]` is seven sentences wide. Nothing has retrieved anything yet; this is purely to make the gap between "what's searched" and "what's eventually shown to the LLM" visible before it matters.

## 3. Ingest, then swap the window back in at query time

```python
    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    # The postprocessor is what replaces the matched sentence with its window.
    query_engine = index.as_query_engine(
        similarity_top_k=2,
        node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")],
    )

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

The ingestion branch is unchanged from Steps 3-4. The one new piece is `node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")]` — this runs *after* retrieval finds the top-k matching sentences, and replaces each one's content with `metadata["window"]` before the LLM prompt is assembled. Without this postprocessor, the LLM would see the same bare single sentences you printed in step 1 — precise matches, but often not enough text to actually answer with.

## Try it (full run)

```bash
uv run 03_sentence_window.py
```

Expected output (LLM wording will vary):

```
Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: The maximum client meal reimbursement per person is $75.

  source (0.819): ## Expense Reimbursement  Employees can be reimbursed for business-related expenses such as travel, ...
  source (0.547): During the last two weeks of December, no more than 30% of any single team may be on vacation simult...
------------------------------------------------------------
Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: All full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days. Unused vacation days can be carried over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at year-end unless local law requires otherwise.
------------------------------------------------------------
```

Look closely at the first answer: it's missing the alcohol rule this time, even though `03`'s whole design goal is more generous context than Steps 3-4. This is a real, honest limitation, not a mistake to fix — with `window_size=3` and `similarity_top_k=2`, the alcohol sentence simply fell outside both retrieved windows. Sentence-window chunking narrows *what gets embedded*, not *how much can go wrong at the edges of a window*. A larger `window_size` or `similarity_top_k` would likely fix this specific question, at the cost of sending more text to the LLM on every query — the same size trade-off from Steps 3-4, just moved to a different knob.

## Checkpoint

<details>
<summary>Full <code>03_sentence_window.py</code></summary>

```python
"""
03 - Sentence-window chunking (SentenceWindowNodeParser)

Each node is a SINGLE sentence -- giving very precise embedding matches
-- but every node's metadata also stores a "window" of the surrounding
sentences. At query time, MetadataReplacementPostProcessor swaps the
matched single sentence back out for its window, so the LLM sees enough
context to actually answer. This is a sentence-granularity form of
parent-child chunking. See ../vector-dbs/chunking.md, section 3 and 7.

Run:
    uv run 03_sentence_window.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_sentence_window"


def main():
    configure_models()

    parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_sentence",
    )
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Sentence-window chunking (1 sentence per node, window=3)")

    # Show that each node's embedded text (1 sentence) differs from the
    # wider window stored in its metadata -- that gap is the whole point.
    sample = nodes[5]
    print("--- Example: embedded sentence vs. stored window ---")
    print(f"Embedded (matched against queries): {sample.get_content()!r}")
    print(f"Window (sent to the LLM instead):   {sample.metadata['window']!r}\n")

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    # The postprocessor is what replaces the matched sentence with its window.
    query_engine = index.as_query_engine(
        similarity_top_k=2,
        node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")],
    )

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

This matches [../rag-with-llamaindex-and-chunking/03_sentence_window.py](../rag-with-llamaindex-and-chunking/03_sentence_window.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| LLM answer is missing detail that's clearly in the document | `window_size` or `similarity_top_k` too small for how far apart the relevant sentences are | Increase one or both — but notice this is the same size trade-off as fixed-size chunking, just relocated |
| `KeyError: 'window'` | Forgot `window_metadata_key="window"` in the parser, or used a different key than the postprocessor's `target_metadata_key` | The parser's `window_metadata_key` and the postprocessor's `target_metadata_key` must match exactly |
| Answers look identical to Step 4's | `node_postprocessors` argument left off `as_query_engine`, so the raw single sentences are used instead of their windows | Confirm `node_postprocessors=[MetadataReplacementPostProcessor(...)]` is passed |
| 35 chunks seems like a lot | Correct — one node per sentence in the whole handbook, by design | Not an error; compare against Steps 3/4's 10 chunks to see the size difference |

Next: **[Semantic Chunking](07-semantic-chunking.md)** — stop picking a chunk size altogether, and let embedding similarity decide where sections end.
