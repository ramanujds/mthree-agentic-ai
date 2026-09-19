# Step 8 — Recap and Exercises

> [Back to index](README.md) · Previous: [Query Engine and Sources](08-query-engine-and-sources.md)

## What you built

One script, from an empty folder: `main.py`, a RAG pipeline that answers questions about two onboarding documents, storing vectors in a Chroma server instead of in memory, and skipping re-ingestion when the collection already has data.

It should now match [../simple-rag-example-chromadb/main.py](../simple-rag-example-chromadb/main.py) exactly.

## Quick reference card

| Concept | Where it lives |
| --- | --- |
| Global model configuration | `Settings.llm` / `Settings.embed_model`, set once in `build_query_engine()` |
| Chroma connection | `chromadb.HttpClient(host=..., port=...)` |
| Collection (Chroma's "table") | `chroma_client.get_or_create_collection(COLLECTION_NAME)` |
| Vector store adapter | `ChromaVectorStore(chroma_collection=...)` |
| Idempotent ingestion | `if chroma_collection.count() == 0: ... else: ...` |
| First-run ingestion | `SimpleDirectoryReader` → `StorageContext.from_defaults(vector_store=...)` → `VectorStoreIndex.from_documents(...)` |
| Reconnecting to existing vectors | `VectorStoreIndex.from_vector_store(vector_store)` |
| Retrieval + generation, bundled | `index.as_query_engine(similarity_top_k=2)` |
| Grounding/traceability | `response.source_nodes`, each carrying `.node.metadata["file_name"]` |

## Gotchas reference

| Symptom | Cause | Fix |
| --- | --- | --- |
| Vector count doubles on every run | Skipped the Step 6 persistence check, or reverted to Step 5's unconditional ingestion | Confirm the `if chroma_collection.count() == 0` branch is in place |
| Edited `data/` but answers don't change | Collection already has data, so ingestion is skipped by design | `docker compose down -v && docker compose up -d` to force a clean re-ingest |
| `from_vector_store` errors about embedding dimension | Changed `OLLAMA_EMBED_MODEL` without resetting the collection | Vectors from different embedding models aren't interchangeable — reset the collection whenever you change embedding models |
| Everything is reachable but the first call is very slow | Ollama loading a model into memory for the first time this session | Normal — subsequent calls are much faster |
| `curl` to Chroma or Ollama fails | One of the two Docker/local services isn't running | Recheck [Step 1](02-environment-setup.md)'s verification commands |

## Discussion questions

1. `chroma_collection.count() == 0` is the entire "has this been ingested before" check. What's a scenario where this check gives the wrong answer (e.g., partial ingestion from a crashed run)? What would a more robust check look like?
2. Why does `VectorStoreIndex.from_vector_store` not need `DATA_DIR` or `SimpleDirectoryReader` at all? What does that tell you about what's actually stored in Chroma versus what's recomputed on demand?
3. `similarity_top_k=2` is hardcoded. What would you need to know about your corpus to pick a better value, and how would you test whether a given value is too low or too high?
4. This app never deletes or updates individual documents — only "ingest everything" or "ingest nothing." What would need to change to support updating a single changed file without a full reset?

## Exercises

Roughly ordered easiest to hardest:

1. **Change the questions.** Edit the `questions` list in `main()` to ask something not directly answered in either file, and observe how the model behaves when retrieval doesn't find a strong match.
2. **Tune `similarity_top_k`.** Try `1` and `4` and compare the answers and sources printed for the existing questions.
3. **Add a third data file.** Drop a new `.txt` file into `data/`, reset the collection (`docker compose down -v && docker compose up -d`), and confirm it gets ingested and can be retrieved from.
4. **Add metadata filtering.** Using [../../vector-dbs/chroma-db-filtering.md](../../vector-dbs/chroma-db-filtering.md) as a reference, restrict retrieval to a specific source file by filename.
5. **Make the collection name configurable.** Currently `COLLECTION_NAME` is hardcoded; add a `CHROMA_COLLECTION` environment variable following the same pattern as the other constants, so multiple corpora can share one Chroma server.
6. **Rebuild `main.py` from a blank file, unaided.** The best test of whether the concepts stuck: close this walkthrough and rewrite it from memory, checking against [../simple-rag-example-chromadb/main.py](../simple-rag-example-chromadb/main.py) only at the end.

## What's next

**[../simple-rag-example-qdrant/](../simple-rag-example-qdrant/README.md)** — the same pipeline, same two documents, same three questions, but backed by Qdrant instead of Chroma. Compare `simple-rag-example-qdrant/main.py` against what you just built: the `Settings`, ingestion branch, and query-engine shape are nearly identical — only the client API for connecting to the vector store and checking whether it's empty changes.
