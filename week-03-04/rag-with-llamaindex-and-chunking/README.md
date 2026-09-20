# RAG with LlamaIndex + Chroma DB: Chunking Strategies

Six runnable examples, each using a different LlamaIndex chunking
strategy against the **same** sample document, so you can directly
compare chunk boundaries and retrieval quality. Companion code for
[../vector-dbs/chunking.md](../vector-dbs/chunking.md) — read that first
for the concepts; this is the "see it for yourself" version.

- **Fully local**: embeddings + LLM run through [Ollama](https://ollama.com) — no API key.
- **Chroma DB via Docker**: each script uses its own collection in the
  same Chroma server, so results don't overwrite each other.
- **Same sample doc for all six**: `data/employee_handbook.md`, a
  multi-section Markdown handbook — long and varied enough to actually
  show differences between strategies (unlike a two-paragraph toy doc).

## Setup

1. Make sure [Ollama](https://ollama.com) is installed and running, and pull the models:

   ```bash
   ollama pull llama3:8b
   ollama pull nomic-embed-text
   ```

2. Start Chroma DB:

   ```bash
   docker compose up -d
   ```

   > If another example's Chroma container is already using port 8000
   > (e.g. `simple-rag-chromadb` from `rag-with-LlamaIndex/simple-rag-example-chromadb`),
   > stop it first or change the port mapping in this folder's `docker-compose.yml`.

3. Install deps:

   ```bash
   uv sync
   ```

4. Run any example:

   ```bash
   uv run 01_fixed_size_chunking.py
   ```

Override `OLLAMA_LLM_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_BASE_URL`,
`CHROMA_HOST`, or `CHROMA_PORT` as environment variables if needed.

## The Six Strategies

| Script | Strategy | LlamaIndex class | Chunking notes section |
|---|---|---|---|
| `01_fixed_size_chunking.py` | Fixed-size token windows, no boundary awareness | `TokenTextSplitter` | §1 |
| `02_sentence_splitter.py` | Recursive splitting (paragraph → sentence → hard cut) | `SentenceSplitter` | §2 |
| `03_sentence_window.py` | One sentence per node, window of context in metadata | `SentenceWindowNodeParser` | §3 / §7 |
| `04_semantic_chunking.py` | Cuts where embedding similarity between sentences drops | `SemanticSplitterNodeParser` | §4 |
| `05_hierarchical_parent_child.py` | Small nodes for search, auto-merged into larger parents | `HierarchicalNodeParser` + `AutoMergingRetriever` | §7 |
| `06_markdown_structure_aware.py` | One chunk per Markdown section (`##` header) | `MarkdownNodeParser` | §5 |

Each script:

1. Parses `data/employee_handbook.md` with its strategy and **prints
   every resulting chunk** (or a preview) so you can see the actual
   boundaries — this is the main point of these examples.
2. Ingests into its own Chroma collection (skipped on repeat runs — the
   collection is checked via `.count()` first, same pattern as the
   other Chroma examples in this repo).
3. Runs the same two test questions through a query engine, so you can
   compare retrieval quality across strategies.

## What to Look For

- **01 vs. 02**: run both and compare the printed chunks. `01`
  (fixed-size) cuts mid-sentence (a chunk can start mid-word/mid-clause);
  `02` (sentence-aware) never does — every chunk starts cleanly.
- **03** (sentence window): notice the printed "embedded sentence vs.
  stored window" — retrieval matches on one sentence, but the LLM sees
  several sentences of surrounding context. Also notice this can
  legitimately *miss* detail that falls just outside the window — a
  real trade-off, not a bug.
- **04** (semantic): chunk boundaries don't line up with `##` headers —
  they follow topic drift in the embedding space instead, which can
  cross section boundaries when the topic doesn't visibly shift.
- **05** (hierarchical): watch for `Merging N nodes into parent node`
  printed at query time — that's `AutoMergingRetriever` promoting
  several small matched chunks up to their shared parent for richer
  context. This script also persists a docstore to
  `.docstore_hierarchical/` (gitignored) — deliberately showing that
  parent-child chunking needs a child→parent map that lives *outside*
  Chroma (Chroma only stores vectors).
- **06** (structure-aware): with this cleanly-headed sample document,
  you get exactly one chunk per policy section — the cleanest possible
  result, and a good illustration of why structure-aware chunking is
  worth it *when* the source document has reliable headers.

## Resetting

To re-run ingestion from scratch (e.g., after editing `data/employee_handbook.md`):

```bash
docker compose down -v   # wipes all six collections
rm -rf .docstore_hierarchical
docker compose up -d
```
