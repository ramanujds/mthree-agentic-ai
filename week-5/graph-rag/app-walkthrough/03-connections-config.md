# Step 2 — Connections and Config

> [Back to index](README.md) · Previous: [Environment Setup](02-environment-setup.md) · Next: [Ingest: Chunking and Schema](04-ingest-chunking-and-schema.md)

## Goal

Build `config.py`: one place that creates the OpenAI chat model and the Neo4j connection, so `ingest.py` and `query.py` never read environment variables themselves.

## Why this matters

Both phases need the same two objects: an LLM and a graph connection. If each file constructed its own, a change like switching model or pointing at a different database would mean editing several files, and the two phases could quietly drift onto different settings. Funnelling both through `get_llm()` and `get_graph()` means one edit changes the whole app.

Two details are worth saying out loud. `temperature=0` matters more here than in a chat app: the LLM is generating *Cypher* and extracting structured data, where you want the same input to give the same output, not creative variation. And `load_dotenv()` runs at import time, so merely importing `config` is enough to make `OPENAI_API_KEY` available to `ChatOpenAI`, which reads it from the environment on its own. You never pass the key explicitly.

## 1. Load the environment and build the LLM

Create `config.py`:

```python
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm() -> ChatOpenAI:
    # Reads OPENAI_API_KEY from the environment (.env)
    return ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o"), temperature=0)
```

`os.getenv("LLM_MODEL", "gpt-4o")` means the model is configurable from `.env` but has a sensible default if the variable is missing.

## 2. Add the graph connection

Add the Neo4j import next to the OpenAI one, and `get_graph()` below `get_llm()`:

```python
from langchain_neo4j import Neo4jGraph
```

```python
def get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password123"),
    )
```

`Neo4jGraph` connects when it is constructed, and it also reads the database's current schema (labels, relationship types, properties) so that later steps can show that schema to the LLM. That means constructing it is itself a connectivity test.

## Try it

```bash
uv run python -c "from config import get_graph, get_llm; print(get_graph().query('RETURN 1 AS ok')); print(get_llm().invoke('Say hi in 3 words').content)"
```

Expected output (the second line will vary):

```
[{'ok': 1}]
Hello there, friend!
```

The first line proves Neo4j is reachable with your credentials. The second proves the OpenAI key works.

## Checkpoint

<details>
<summary>Full <code>config.py</code></summary>

```python
import os

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm() -> ChatOpenAI:
    # Reads OPENAI_API_KEY from the environment (.env)
    return ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o"), temperature=0)


def get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password123"),
    )
```

</details>

This matches [../app/config.py](../app/config.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ServiceUnavailable` or `Cannot resolve address` | Neo4j is not running or still starting | `docker compose ps`; wait for it, then retry |
| `ValueError: Could not use APOC procedures` | `Neo4jGraph` needs the APOC plugin and the container was started without it | Add the two APOC lines from Step 1 to `docker-compose.yml` and recreate the container |
| `AuthError: The client is unauthorized` | Password in `.env` does not match `NEO4J_AUTH` in `docker-compose.yml` | Make both say `password123`, or `docker compose down -v` and restart |
| `openai.AuthenticationError` or "api_key must be set" | `.env` missing, in the wrong folder, or still holds the placeholder | Put a real key in `.env` next to `config.py` and run from that folder |
| `ModuleNotFoundError: dotenv` | Running `python` directly instead of through uv | Use `uv run ...` so the project environment is used |

Next: **[Ingest: Chunking and Schema](04-ingest-chunking-and-schema.md)**.
