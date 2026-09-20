# Step 7 — Hierarchical / Parent-Child Chunking

> [Back to index](README.md) · Previous: [Semantic Chunking](07-semantic-chunking.md) · Next: [Structure-Aware Chunking](09-structure-aware-chunking.md)

## Goal

Build `05_hierarchical_parent_child.py`: split the handbook into three nested chunk sizes with `HierarchicalNodeParser`, embed only the smallest ("leaf") nodes, and use `AutoMergingRetriever` to automatically hand back a larger parent chunk when enough of its children match a query.

## Why this matters

Step 5 solved the size trade-off at sentence granularity with a fixed window. Hierarchical chunking generalizes the same idea: build a tree of chunk sizes (here, 1024 → 256 → 64 tokens), embed and search only the smallest, most precise level, but let the retriever *automatically* promote a match up to its parent — the middle or top-level chunk — when several sibling leaves under the same parent all matched. You get precise search and rich, variable-sized context, without picking one fixed window size up front.

This is also the step where a real cost of parent-child chunking, flagged in [../vector-dbs/chunking.md, section 7](../vector-dbs/chunking.md), becomes unavoidable to confront: the parent/child relationships between nodes have to live **somewhere**, and Chroma isn't it — Chroma only stores vectors. That relationship map lives in a separate structure called a **docstore**. Every other script in this walkthrough could ignore the docstore because they never needed one; this one can't skip it, and you'll persist it to disk yourself so parent-child retrieval survives a process restart, not just the vectors.

## 1. Build the three-level hierarchy and look at both levels

```python
"""
05 - Hierarchical / parent-child chunking (HierarchicalNodeParser + AutoMergingRetriever)

Splits the document into three chunk sizes (large -> medium -> small),
keeping parent/child relationships between them. Only the SMALL "leaf"
nodes are embedded and searched; when enough leaf nodes under the same
parent match a query, AutoMergingRetriever automatically returns the
larger parent chunk instead -- giving the LLM richer context without
losing retrieval precision. See ../vector-dbs/chunking.md, section 7.

Because the parent/child relationships live in a docstore (not in
Chroma, which only stores vectors), this script persists that docstore
to disk itself -- illustrating chunking.md's pitfall that hierarchical
chunking "doubles the indexing complexity": you need to track the
child-to-parent map yourself, not just the vectors.

Run:
    uv run 05_hierarchical_parent_child.py
"""

import os

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_hierarchical"
DOCSTORE_PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".docstore_hierarchical")


def main():
    configure_models()

    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[1024, 256, 64])
    document = Document(text=load_handbook_text())
    all_nodes = parser.get_nodes_from_documents([document])
    leaf_nodes = get_leaf_nodes(all_nodes)
    print_nodes(all_nodes, "All nodes across 3 levels (1024/256/64 tokens)")
    print_nodes(leaf_nodes, "Leaf nodes only (these get embedded + searched)")
```

`chunk_sizes=[1024, 256, 64]` builds three layers: one large ~1024-token chunk per major stretch of text, each split into ~256-token chunks, each of those split again into ~64-token chunks. `get_leaf_nodes(all_nodes)` filters down to just the bottom layer — the ones with no children of their own — because those are the only ones that get embedded.

## Try it

```bash
uv run 05_hierarchical_parent_child.py
```

Expected output (truncated):

```
=== All nodes across 3 levels (1024/256/64 tokens): 26 chunk(s) ===
[0] (5027 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
[1] (1277 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
...

=== Leaf nodes only (these get embedded + searched): 21 chunk(s) ===
[0] (219 chars) # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted...
[1] (219 chars) Requests must be submitted at least 2 business days in advance through the HR portal. Fully remote arrangements are only available to employees in roles explici...
...
```

26 nodes total across all three levels, but only 21 of them are leaves — the rest are the larger parent/grandparent nodes that exist purely to be promoted to later, never embedded directly.

## 2. Build a docstore alongside the vector store, and persist it

```python
    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        # Fresh collection: build a docstore with ALL nodes (leaves +
        # parents) so the retriever can resolve a leaf match up to its
        # parent, then persist it -- the docstore is what makes
        # parent-child retrieval possible, and it lives outside Chroma.
        docstore = SimpleDocumentStore()
        docstore.add_documents(all_nodes)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
        storage_context.persist(persist_dir=DOCSTORE_PERSIST_DIR)
    else:
        # Reuse the persisted vectors AND the persisted docstore -- without
        # the docstore, auto-merging has no parent/child map to work with.
        docstore = SimpleDocumentStore.from_persist_dir(DOCSTORE_PERSIST_DIR)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(nodes=[], storage_context=storage_context)
```

Notice two differences from every previous script's ingestion branch: `docstore.add_documents(all_nodes)` stores **all** 26 nodes — leaves and parents both — because the retriever needs the parents on hand to promote a match to, even though only the 21 leaves get embedded into `VectorStoreIndex(leaf_nodes, ...)`. And `storage_context.persist(persist_dir=DOCSTORE_PERSIST_DIR)` writes that docstore to a local folder — Chroma has no idea this relationship map exists, so if you didn't persist it yourself, a second run would reconnect to the right vectors but have completely lost which parent each one belongs to.

The `else` branch reloads that persisted docstore with `SimpleDocumentStore.from_persist_dir(...)` and pairs it with the existing vector store. `VectorStoreIndex(nodes=[], storage_context=storage_context)` is worth pausing on: passing an empty node list means nothing new gets embedded — this just wraps the storage context (vectors already in Chroma, docstore already on disk) into an `index` object with no extra work.

## 3. Wrap retrieval with `AutoMergingRetriever`

```python
    base_retriever = index.as_retriever(similarity_top_k=6)
    merging_retriever = AutoMergingRetriever(base_retriever, index.storage_context, verbose=True)
    query_engine = RetrieverQueryEngine.from_args(merging_retriever)

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

`similarity_top_k=6` deliberately retrieves more leaf candidates than the `2` used in every earlier script — with much smaller leaves (many are well under 256 tokens), you need more of them in play for `AutoMergingRetriever` to notice when several share a parent. That's exactly what it checks: if enough of the top-k leaves turn out to be children of the same parent node, it discards the individual leaves and returns the parent instead. `verbose=True` prints that decision as it happens. `RetrieverQueryEngine.from_args(merging_retriever)` is a lower-level constructor than the `index.as_query_engine(...)` used everywhere else — needed here because the retriever itself (`merging_retriever`, not `index`) is now doing something nontrivial, and there's no plain index to build a query engine from directly.

## Try it

```bash
uv run 05_hierarchical_parent_child.py
```

Expected output (LLM wording will vary; the `Merging` lines will not):

```
> Merging 3 nodes into parent node.
> Parent node id: 33dcf33b-27e4-46ce-b7cd-941d1a7506d7.
> Parent node text: # Acme Corp Employee Handbook

## Remote Work Policy

Employees may work remotely up to 3 days pe...

Q: What is the maximum client meal reimbursement per person, and what's the rule about alcohol?
A: Client meal reimbursements are capped at $75 per person, and alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

  source (0.701): Reimbursements are processed within 10 business days of approval and are paid out via direct deposit...
  source (0.522): ## Expense Reimbursement  Employees can be reimbursed for business-related expenses such as travel, ...
  source (0.410): The onboarding buddy program runs for the new hire's first 30 days, with a mandatory check-in at the...
  source (0.403): # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per w...
------------------------------------------------------------
> Merging 3 nodes into parent node.
> Parent node id: 33dcf33b-27e4-46ce-b7cd-941d1a7506d7.
...
> Merging 3 nodes into parent node.
> Parent node id: 63a217dd-7803-4166-bd60-e8791e0995e0.
...

Q: How many vacation days do employees accrue per year, and how many can be carried over?
A: 18 days of paid vacation per year, and up to a maximum of 5 days can be carried over to the next year.

  source (0.629): # Acme Corp Employee Handbook  ## Remote Work Policy  Employees may work remotely up to 3 days per w...
  source (0.599): During the last two weeks of December, no more than 30% of any single team may be on vacation simult...
------------------------------------------------------------
```

Those `> Merging N nodes into parent node` lines are the mechanism working live: three retrieved leaves turned out to share a parent, so `AutoMergingRetriever` replaced them with that one larger chunk before it ever reached the LLM. Notice the first answer's `source` lines are *longer* than a single 64-token leaf — that's the merged parent, not a leaf.

## 4. Confirm persistence actually survives a restart

```bash
uv run 05_hierarchical_parent_child.py
```

Run it a second time. The `chroma_collection.count() == 0` check is now false, so ingestion is skipped entirely — but the merging behavior and answers should look the same, because `SimpleDocumentStore.from_persist_dir(...)` reloaded the exact same parent/child map from `.docstore_hierarchical/`. If you delete that folder but leave the Chroma collection alone, try running it again and see what breaks — that's Exercise 3 in the recap.

## Checkpoint

<details>
<summary>Full <code>05_hierarchical_parent_child.py</code></summary>

```python
"""
05 - Hierarchical / parent-child chunking (HierarchicalNodeParser + AutoMergingRetriever)

Splits the document into three chunk sizes (large -> medium -> small),
keeping parent/child relationships between them. Only the SMALL "leaf"
nodes are embedded and searched; when enough leaf nodes under the same
parent match a query, AutoMergingRetriever automatically returns the
larger parent chunk instead -- giving the LLM richer context without
losing retrieval precision. See ../vector-dbs/chunking.md, section 7.

Because the parent/child relationships live in a docstore (not in
Chroma, which only stores vectors), this script persists that docstore
to disk itself -- illustrating chunking.md's pitfall that hierarchical
chunking "doubles the indexing complexity": you need to track the
child-to-parent map yourself, not just the vectors.

Run:
    uv run 05_hierarchical_parent_child.py
"""

import os

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_hierarchical"
DOCSTORE_PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".docstore_hierarchical")


def main():
    configure_models()

    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[1024, 256, 64])
    document = Document(text=load_handbook_text())
    all_nodes = parser.get_nodes_from_documents([document])
    leaf_nodes = get_leaf_nodes(all_nodes)
    print_nodes(all_nodes, "All nodes across 3 levels (1024/256/64 tokens)")
    print_nodes(leaf_nodes, "Leaf nodes only (these get embedded + searched)")

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        # Fresh collection: build a docstore with ALL nodes (leaves +
        # parents) so the retriever can resolve a leaf match up to its
        # parent, then persist it -- the docstore is what makes
        # parent-child retrieval possible, and it lives outside Chroma.
        docstore = SimpleDocumentStore()
        docstore.add_documents(all_nodes)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
        storage_context.persist(persist_dir=DOCSTORE_PERSIST_DIR)
    else:
        # Reuse the persisted vectors AND the persisted docstore -- without
        # the docstore, auto-merging has no parent/child map to work with.
        docstore = SimpleDocumentStore.from_persist_dir(DOCSTORE_PERSIST_DIR)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(nodes=[], storage_context=storage_context)

    base_retriever = index.as_retriever(similarity_top_k=6)
    merging_retriever = AutoMergingRetriever(base_retriever, index.storage_context, verbose=True)
    query_engine = RetrieverQueryEngine.from_args(merging_retriever)

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

This matches [../rag-with-llamaindex-and-chunking/05_hierarchical_parent_child.py](../rag-with-llamaindex-and-chunking/05_hierarchical_parent_child.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| No `Merging` lines ever print | `similarity_top_k` too low for enough sibling leaves to appear together, or `chunk_sizes` levels too far apart | Raise `similarity_top_k`, or narrow the gaps between `chunk_sizes` |
| Second run raises a file-not-found error on `.docstore_hierarchical` | Deleted the folder without also resetting the Chroma collection (`docker compose down -v`) | Reset both together — the vectors and the docstore must go out of sync never separately |
| `AutoMergingRetriever` returns leaves instead of a merged parent | Not enough of the top-k leaves share a common parent — this is correct behavior, not a bug | Increase `similarity_top_k`, or accept that merging is conditional, not guaranteed, on every query |
| `.docstore_hierarchical/` growing every run | Not applicable here — `persist()` only runs in the fresh-ingestion branch, so it's written once, not appended | If you see repeated writes, check the `if chroma_collection.count() == 0` branch didn't get bypassed |

Next: **[Structure-Aware Chunking](09-structure-aware-chunking.md)** — the last strategy: let the document's own Markdown headers decide the boundaries.
