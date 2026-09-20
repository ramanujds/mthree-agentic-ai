# simple-rag-example-chromadb

A RAG example using LlamaIndex + [Chroma DB](https://www.trychroma.com/) as
a real vector store, instead of the in-memory `VectorStoreIndex` in
[../simple-rag-example](../simple-rag-example). See
[../../vector-dbs/chroma-db-intro.md](../../vector-dbs/chroma-db-intro.md)
for background on Chroma DB itself.

- **Chroma DB via Docker**: Chroma runs as its own server (client-server
  mode), started with `docker compose`, and persists embeddings to a
  named volume so they survive restarts.
- **Fully local otherwise**: both the embedding model and the LLM run
  through [Ollama](https://ollama.com) — no API key, no data leaving your
  machine (Chroma also runs locally in Docker).

## Setup

1. Make sure [Ollama](https://ollama.com) is installed and running
   (the desktop app, `ollama serve`, or a Docker container all work —
   this just needs `http://localhost:11434` to respond), and pull the
   models used by this example (one-time):

   ```bash
   ollama pull llama3:8b
   ollama pull nomic-embed-text
   ```

2. Start Chroma DB:

   ```bash
   docker compose up -d
   ```

   This starts a Chroma server on `http://localhost:8000`, persisting
   data to the `chroma_data` Docker volume. Check it's up with:

   ```bash
   curl http://localhost:8000/api/v2/heartbeat
   ```

3. Install Python deps and run:

   ```bash
   uv sync
   uv run main.py
   ```

Override `OLLAMA_LLM_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_BASE_URL`,
`CHROMA_HOST`, or `CHROMA_PORT` as environment variables if you want to
point at different models or a remote Chroma/Ollama instance.

## What it does

1. Connects to the Chroma server and gets (or creates) a collection
   named `onboarding_docs`.
2. **First run**: the collection is empty, so it loads the two sample
   text files from `data/` with `SimpleDirectoryReader`, chunks +
   embeds them (locally, via Ollama), and stores the vectors in Chroma.
3. **Subsequent runs**: the collection already has data, so it skips
   re-ingesting and reconnects straight to the existing vectors —
   demonstrating that Chroma persists across process restarts, unlike
   the in-memory version.
4. Asks 3 questions through a query engine (`as_query_engine`), which
   retrieves the relevant chunks from Chroma and asks the local LLM to
   answer using them.
5. Prints each answer along with which source file(s) it was grounded in.

To force re-ingestion (e.g., after changing files in `data/`), reset the
collection:

```bash
docker compose down -v   # wipes the chroma_data volume
docker compose up -d
```

## Stopping

```bash
docker compose down      # stop Chroma, keep the data volume
docker compose down -v   # stop Chroma and delete stored vectors
```
