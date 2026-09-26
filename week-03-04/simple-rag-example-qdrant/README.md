# simple-rag-example-qdrant

A RAG example using LlamaIndex + [Qdrant](https://qdrant.tech/) as a real
vector store, instead of the in-memory `VectorStoreIndex` in
[../rag-with-LlamaIndex/simple-rag-example](../rag-with-LlamaIndex/simple-rag-example).
See [../../vector-dbs/qdrant-intro.md](../../vector-dbs/qdrant-intro.md)
for background on Qdrant itself, and
[../simple-rag-example-chromadb](../simple-rag-example-chromadb) for the
equivalent example built on Chroma DB.

- **Qdrant via Docker**: Qdrant runs as its own server, started with
  `docker compose`, and persists points to a named volume so they survive
  restarts.
- **Fully local otherwise**: both the embedding model and the LLM run
  through [Ollama](https://ollama.com) — no API key, no data leaving your
  machine (Qdrant also runs locally in Docker).

## Setup

1. Make sure [Ollama](https://ollama.com) is installed and running
   (the desktop app, `ollama serve`, or a Docker container all work —
   this just needs `http://localhost:11434` to respond), and pull the
   models used by this example (one-time):

   ```bash
   ollama pull llama3:8b
   ollama pull nomic-embed-text
   ```

2. Start Qdrant:

   ```bash
   docker compose up -d
   ```

   This starts a Qdrant server with its REST API on `http://localhost:6333`
   (gRPC on `6334`), persisting data to the `qdrant_data` Docker volume.
   Check it's up with:

   ```bash
   curl http://localhost:6333/healthz
   ```

3. Install Python deps and run:

   ```bash
   uv sync
   uv run main.py
   ```

Override `OLLAMA_LLM_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_BASE_URL`,
`QDRANT_HOST`, or `QDRANT_PORT` as environment variables if you want to
point at different models or a remote Qdrant/Ollama instance.

## What it does

1. Connects to the Qdrant server and checks for a collection named
   `onboarding_docs`.
2. **First run**: the collection doesn't exist (or is empty), so it loads
   the two sample text files from `data/` with `SimpleDirectoryReader`,
   chunks + embeds them (locally, via Ollama), and stores the resulting
   points in Qdrant.
3. **Subsequent runs**: the collection already has points, so it skips
   re-ingesting and reconnects straight to the existing vectors —
   demonstrating that Qdrant persists across process restarts, unlike
   the in-memory version.
4. Asks 3 questions through a query engine (`as_query_engine`), which
   retrieves the relevant chunks from Qdrant and asks the local LLM to
   answer using them.
5. Prints each answer along with which source file(s) it was grounded in.

To force re-ingestion (e.g., after changing files in `data/`), reset the
collection:

```bash
docker compose down -v   # wipes the qdrant_data volume
docker compose up -d
```

## Stopping

```bash
docker compose down      # stop Qdrant, keep the data volume
docker compose down -v   # stop Qdrant and delete stored points
```
