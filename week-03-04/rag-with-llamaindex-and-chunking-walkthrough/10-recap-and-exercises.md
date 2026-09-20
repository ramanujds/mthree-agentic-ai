# Step 9 — Recap and Exercises

> [Back to index](README.md) · Previous: [Structure-Aware Chunking](09-structure-aware-chunking.md)

## What you built

One shared `common.py`, plus six independent scripts — each parsing the same `data/employee_handbook.md` with a different chunking strategy, ingesting into its own Chroma collection, and answering the same two questions:

| Script | Strategy |
| --- | --- |
| `01_fixed_size_chunking.py` | `TokenTextSplitter` — fixed token windows, no boundary awareness |
| `02_sentence_splitter.py` | `SentenceSplitter` — recursive splitting on paragraph/sentence boundaries |
| `03_sentence_window.py` | `SentenceWindowNodeParser` + `MetadataReplacementPostProcessor` |
| `04_semantic_chunking.py` | `SemanticSplitterNodeParser` — boundaries from embedding-similarity drops |
| `05_hierarchical_parent_child.py` | `HierarchicalNodeParser` + `AutoMergingRetriever` |
| `06_markdown_structure_aware.py` | `MarkdownNodeParser` — one chunk per `##` section |

All six should now match their counterparts in [../rag-with-llamaindex-and-chunking/](../rag-with-llamaindex-and-chunking/) exactly.

## Quick reference card

| Concept | Where it lives |
| --- | --- |
| Shared model/Chroma/print setup | `common.py` |
| A per-node text preview | `common.print_nodes(nodes, label)` |
| Idempotent ingestion (the pattern every script reuses) | `if chroma_collection.count() == 0: ... else: ...` |
| Fixed-size, boundary-blind chunking | `TokenTextSplitter(chunk_size=..., chunk_overlap=...)` |
| Recursive, boundary-aware chunking | `SentenceSplitter(chunk_size=..., chunk_overlap=...)` |
| One-sentence-per-node with a wider retrieval window | `SentenceWindowNodeParser.from_defaults(window_size=...)` + `MetadataReplacementPostProcessor` |
| Topic-drift-based chunking | `SemanticSplitterNodeParser(buffer_size=..., breakpoint_percentile_threshold=..., embed_model=...)` |
| Parent/child chunk tree | `HierarchicalNodeParser.from_defaults(chunk_sizes=[...])` + `get_leaf_nodes(...)` |
| Automatic promotion of matched children to their parent | `AutoMergingRetriever(base_retriever, storage_context, verbose=True)` |
| Where parent/child relationships actually live | A `SimpleDocumentStore`, persisted separately from Chroma |
| Header-based chunking | `MarkdownNodeParser()` |

## Gotchas reference

| Symptom | Cause | Fix |
| --- | --- | --- |
| A chunk starts mid-sentence | Used `TokenTextSplitter`, which has no boundary awareness by design | Expected behavior in Step 3; switch to `SentenceSplitter` (Step 4) if this matters for your data |
| An answer is missing a detail you know is in the document | Retrieved window/chunk/top-k too narrow for that specific fact's context | Increase `window_size`, `similarity_top_k`, or chunk size — the same trade-off resurfaces in every strategy, just relocated to a different knob |
| Second run of any script doesn't reflect an edited `data/employee_handbook.md` | Every script's `count() == 0` check causes it to skip re-ingesting once a collection has data — by design | `docker compose down -v && docker compose up -d` to force a clean re-ingest across all six collections |
| `05_hierarchical_parent_child.py`'s second run behaves oddly after deleting `.docstore_hierarchical/` but not resetting Chroma | Vectors and the parent/child docstore fell out of sync — they must be reset together | Always reset both, or neither |
| Semantic chunking (`04`) is much slower to ingest than the others | Every sentence gets embedded once to find boundaries, then again for the final chunks | Expected — this is the real ingestion-cost trade-off from [../vector-dbs/chunking.md, section 4](../vector-dbs/chunking.md) |

## Discussion questions

1. Steps 3 and 4 both answered the two test questions correctly despite very different chunk boundaries. What would you need to change about the questions (or the document) to make the difference between `TokenTextSplitter` and `SentenceSplitter` actually change an answer, not just the printed chunk boundaries?
2. Step 5's sentence-window answer dropped the alcohol clause. Was increasing `window_size` or `similarity_top_k` the better fix, and how would you decide between them without just trying both?
3. Step 6 (semantic) produced chunk boundaries that ignored the document's own `##` headers. Under what circumstances would you actually want that — i.e., when is topic-similarity a better signal than the author's own section breaks?
4. Step 7 needs a docstore that Chroma doesn't provide. Name one other chunking strategy from [../vector-dbs/chunking.md](../vector-dbs/chunking.md) that this walkthrough didn't build, and work out whether it would also need extra state living outside the vector store.
5. Every script uses `similarity_top_k=2`, except Step 7's `6`. If you had to pick one strategy and one `top_k` value to run in production for this handbook, which would you pick, and what would you need to measure to justify it?

## Exercises

Roughly ordered easiest to hardest:

1. **Break the "correct despite different chunks" pattern.** Add a question to two or three scripts whose answer depends on a fact very close to a chunk boundary in `01`/`02` (e.g., something right before or after a section split), and see whether `01` (fixed-size) actually gets it wrong where `02` (sentence-aware) doesn't.
2. **Tune one parameter per strategy.** Try `chunk_size=60` in `01`/`02`, `window_size=1` in `03`, `breakpoint_percentile_threshold=75` in `04`, and observe how the chunk count and answer quality shift in each case.
3. **Break hierarchical persistence on purpose.** Delete `.docstore_hierarchical/` but leave the `chunking_hierarchical` Chroma collection alone, then run `05` again. Read the error, and explain in one sentence why it happened — this is the "doubles the indexing complexity" pitfall from the chunking notes, made concrete.
4. **Add a metadata filter to structure-aware chunking.** Using [../vector-dbs/chroma-db-filtering.md](../vector-dbs/chroma-db-filtering.md) as a reference, filter `06`'s query to only search chunks under a specific section by using the `header_path` metadata each node carries.
5. **Add a seventh script.** Pick one strategy from [../vector-dbs/chunking.md](../vector-dbs/chunking.md) that wasn't built here — proposition-based or late chunking are good candidates — and implement it against the same handbook, following the same `print_nodes` → ingest-if-empty → query pattern every other script uses.
6. **Rebuild `05_hierarchical_parent_child.py` from memory.** It's the most involved script in this walkthrough — the one with a second storage mechanism, not just a different parser. Close this walkthrough, rewrite it from a blank file, and diff your version against [../rag-with-llamaindex-and-chunking/05_hierarchical_parent_child.py](../rag-with-llamaindex-and-chunking/05_hierarchical_parent_child.py) only at the end.

## What's next

There's no further app in this series, but two documents extend directly from what you just built:

- [../vector-dbs/chunking.md](../vector-dbs/chunking.md) — the conceptual reference this walkthrough was based on, including four strategies (document-type-specific, proposition-based, agentic/LLM-based, and late chunking) not built here, and a decision framework for picking a strategy in a real project.
- [../vector-dbs/scaling-rag-with-chroma-db.md](../vector-dbs/scaling-rag-with-chroma-db.md) — what changes about chunking, indexing, and Chroma DB usage once a corpus grows far past one handbook.
