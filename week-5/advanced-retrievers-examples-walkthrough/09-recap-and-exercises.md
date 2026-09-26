# Step 8 — Recap and Exercises

> [Back to index](README.md) · Previous: [Query Fusion Retriever](08-query-fusion-retriever.md)

## What you built

Six independent scripts under `advanced-retrievers-examples/`, each demonstrating a different LlamaIndex retriever against a shared `data/` folder, all running fully locally through Ollama. Every script's final checkpoint matches its counterpart in [../advanced-retrievers-examples/](../advanced-retrievers-examples/) exactly.

## Quick reference card

| Concept | Where it lives |
| --- | --- |
| Baseline semantic retrieval | `VectorIndexRetriever(index=..., similarity_top_k=...)` — [01_vector_index_retriever.py](../advanced-retrievers-examples/01_vector_index_retriever.py) |
| Keyword retrieval, no embeddings | `BM25Retriever.from_defaults(nodes=..., similarity_top_k=...)` — [02_bm25_retriever.py](../advanced-retrievers-examples/02_bm25_retriever.py) |
| Document-level filtering via summaries | `DocumentSummaryIndex.from_documents(...)` + `DocumentSummaryIndexLLMRetriever` / `DocumentSummaryIndexEmbeddingRetriever` (from `llama_index.core.indices.document_summary`) — [03_document_summary_index_retriever.py](../advanced-retrievers-examples/03_document_summary_index_retriever.py) |
| Hierarchical chunking | `HierarchicalNodeParser.from_defaults(chunk_sizes=[...])` + `get_leaf_nodes` — [04_auto_merging_retriever.py](../advanced-retrievers-examples/04_auto_merging_retriever.py) |
| Merge-on-majority rule | `AutoMergingRetriever(base_retriever, storage_context)` — merges when >50% of a parent's children are retrieved |
| Cross-document reference following | `IndexNode(text=..., index_id=...)` + `RecursiveRetriever(root_id, retriever_dict=...)` — [05_recursive_retriever.py](../advanced-retrievers-examples/05_recursive_retriever.py) |
| Combining retrievers | `QueryFusionRetriever([retriever_a, retriever_b], mode=..., num_queries=...)` — [06_query_fusion_retriever.py](../advanced-retrievers-examples/06_query_fusion_retriever.py) |
| Retriever vs. query engine | `.retrieve(query)` returns raw `NodeWithScore` objects; `.query(query)` additionally calls an LLM to synthesize an answer (not used anywhere in this walkthrough) |

## Gotchas reference

| Symptom | Cause | Fix |
| --- | --- | --- |
| `openai.OpenAIError` about a missing API key | `Settings.embed_model` wasn't set before building an index — LlamaIndex's default embedding model expects OpenAI | Always set `Settings.embed_model` (and `Settings.llm`, if used) before creating any index |
| `ImportError` for `DocumentSummaryIndexEmbeddingRetriever` from `llama_index.core.retrievers` | That retriever pair actually lives in `llama_index.core.indices.document_summary`, unlike every other retriever in this project | Import from the correct submodule (Step 4) |
| `AutoMergingRetriever` never merges anything | Chunk sizes give each parent too many children for any realistic `similarity_top_k` to cross the 50% threshold | Pick chunk sizes with a small, predictable number of children per parent (Step 5 uses ~3) |
| `RecursiveRetriever` never recurses into a cited paper | The citation `IndexNode`'s text doesn't score high enough to be retrieved in the entry-point paper's own top-k | Raise that retriever's `similarity_top_k`, or make the citation blurb's wording closer to likely queries (Step 6) |
| A script's index picks up files meant for a different script | `SimpleDirectoryReader` was pointed at all of `DATA_DIR` instead of an explicit `input_files=[...]` list | Every script in this walkthrough always lists its exact files |

## Discussion questions

1. Why does the Document Summary Index Retriever always return the original document's chunks, and never the summary text itself? What would go wrong if it returned the summary instead?
2. `AutoMergingRetriever`'s docstore has to contain every level of node, but only the leaves get embedded. What does that split tell you about which operations are expensive (embedding) versus cheap (storing text for lookup) in this pipeline?
3. In the Recursive Retriever example, what would happen if the citation graph had a cycle (paper A cites B, B cites A)? What would need to change in `RecursiveRetriever`'s design to make cycles safe?
4. `BM25Retriever` needs neither `Settings.embed_model` nor `Settings.llm`. What does that tell you about what it can and can't ever be good at, no matter how it's tuned?
5. `QueryFusionRetriever`'s three modes produced the same *ranking* on this walkthrough's one example query but different score scales. Can you construct a query where the ranking itself — not just the scores — would differ between `reciprocal_rerank` and `relative_score`?

## Exercises

Roughly ordered easiest to hardest:

1. **Change the questions.** Edit the hardcoded `question`/`questions` in any script and observe how each retriever's results shift.
2. **Tune `similarity_top_k`.** Try `1` and `5` in `01_vector_index_retriever.py` and `02_bm25_retriever.py` and compare.
3. **Add a third HR document.** Drop a new `.txt` file into `data/`, add it to the `input_files=[...]` list in `03_document_summary_index_retriever.py`, and confirm a third summary gets generated.
4. **Extend the citation graph.** Add a fourth paper that the `agents` paper also cites directly, and confirm the verbose trace in `05_recursive_retriever.py` shows it being entered.
5. **Enable query paraphrasing.** Set `num_queries=3` in `06_query_fusion_retriever.py` and observe how the LLM-generated paraphrases change which chunks get retrieved.
6. **Rebuild `05_recursive_retriever.py` from memory.** It's the most conceptually involved script in this walkthrough — close this walkthrough, rewrite it from a blank file, and diff against [../advanced-retrievers-examples/05_recursive_retriever.py](../advanced-retrievers-examples/05_recursive_retriever.py) only at the end.

## What's next

This walkthrough stopped at `.retrieve()` everywhere — no script here ever calls an LLM to synthesize a final answer from retrieved nodes (`03_document_summary_index_retriever.py` calls the LLM only to build the index, not to answer questions). Wrapping any of these six retrievers in a `RetrieverQueryEngine` and calling `.query()` instead of `.retrieve()` — the same pattern [../simple-rag-example-chromadb-walkthrough/](../simple-rag-example-chromadb-walkthrough/README.md) already builds around a plain `VectorIndexRetriever` — is a natural follow-on exercise: swap in the BM25, auto-merging, recursive, or fusion retriever from this walkthrough in place of that walkthrough's vector retriever, and see how the final synthesized answers change.

For the underlying concepts across all six retrievers with additional diagrams, see [../../advanced-rag/llamaindex-advanced-retrievers.md](../../advanced-rag/llamaindex-advanced-retrievers.md).
