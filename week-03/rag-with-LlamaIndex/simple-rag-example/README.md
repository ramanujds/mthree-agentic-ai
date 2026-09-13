# simple-rag-example

A minimal RAG example using LlamaIndex only — no vector database, no
LangChain. See [../simple-notes.md](../simple-notes.md) for the concepts
behind why this works.

- **No vector DB**: `VectorStoreIndex` stores vectors in memory, which is
  enough for a handful of documents.
- **No LangChain**: LlamaIndex handles loading, chunking, embedding,
  retrieval, and querying on its own.
- **Local embeddings**: uses a small HuggingFace model
  (`BAAI/bge-small-en-v1.5`) so no embedding API key is needed.
- **Anthropic LLM**: generates the final answer, so an `ANTHROPIC_API_KEY`
  is required.

## Setup

```bash
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
uv run main.py
```

## What it does

1. Loads two sample text files from `data/` (a company policy doc and an
   onboarding FAQ) with `SimpleDirectoryReader`.
2. Chunks + embeds them into an in-memory `VectorStoreIndex`.
3. Asks 3 questions through a query engine (`as_query_engine`), which
   retrieves the relevant chunks and asks Claude to answer using them.
4. Prints each answer along with which source file(s) it was grounded in.

Try changing the questions in `main.py`, or dropping your own `.txt` /
`.md` / `.pdf` files into `data/`.
