# Step 1 — Environment Setup

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Connections and Config](03-connections-config.md)

## Goal

Scaffold the uv project, start a local Neo4j with Docker Compose, create the `.env` file, and add the sample documents the app will turn into a graph.

## Why this matters

This app talks to two external services: Neo4j (a database) and OpenAI (an LLM). If either is unreachable, every later step fails with a connection or authentication error that has nothing to do with the graph code you are about to write. Confirming both once, up front, saves you from debugging the wrong layer.

Two decisions made here ripple through every later file. First, all connection details live in environment variables with matching defaults in code, so nothing is hardcoded to one machine. Second, the sample data is five short paragraphs where the interesting fact (a sanctioned owner) is split across three of them. That split is deliberate: it is the multi-hop case a knowledge graph exists to solve.

## 1. Scaffold the uv project

```bash
mkdir kg-app && cd kg-app
uv init --name kg-app --app --python 3.12 --vcs none .
```

`--vcs none` skips creating a git repository. This creates `pyproject.toml`, `main.py`, `README.md`, and `.python-version`. You will overwrite `main.py` in Step 6.

## 2. Add the dependencies

```bash
uv add langchain langchain-neo4j langchain-openai langchain-experimental langchain-text-splitters python-dotenv
```

| Package | Used for |
| --- | --- |
| `langchain-neo4j` | `Neo4jGraph` (connection) and `GraphCypherQAChain` (question to Cypher to answer) |
| `langchain-openai` | `ChatOpenAI`, the LLM client |
| `langchain-experimental` | `LLMGraphTransformer`, which turns text into graph nodes and edges |
| `langchain-text-splitters` | `RecursiveCharacterTextSplitter` for chunking |
| `python-dotenv` | Loads `.env` into environment variables |
| `langchain` | Core LangChain, pulled in as the base |

Your `pyproject.toml` dependency list should end up like this (exact version floors depend on what uv resolves today):

```toml
dependencies = [
    "langchain>=1.4.3",
    "langchain-experimental>=0.4.2",
    "langchain-neo4j>=0.10.0",
    "langchain-openai>=1.6.7",
    "langchain-text-splitters>=1.1.3",
    "python-dotenv>=1.2.4",
]
```

## 3. Start Neo4j

Create `docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5
    container_name: kg-neo4j
    ports:
      - "7474:7474" # browser UI
      - "7687:7687" # bolt
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]' # langchain-neo4j needs APOC to read the schema
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

Start it:

```bash
docker compose up -d
```

The two `NEO4J_PLUGINS` / `NEO4J_dbms_security_procedures_unrestricted` lines install the APOC plugin and allow its procedures. They are not optional: `Neo4jGraph` calls `apoc.meta.data()` to read the schema when it connects, and refuses to start without it. Port `7687` is the Bolt protocol the Python driver uses. Port `7474` is the web UI. The named volume `neo4j_data` keeps your graph across container restarts. Give Neo4j 20-30 seconds to finish starting, then open `http://localhost:7474` and log in with `neo4j` / `password123`. If the browser asks you to change the password, do not; the app's defaults assume `password123`.

## 4. Create `.env`

```
OPENAI_API_KEY=sk-your-real-key
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
LLM_MODEL=gpt-4o
```

`gpt-4o` is deliberate. In testing, `gpt-4o-mini` dropped facts during extraction and reversed the Zenith to Acme ownership direction, which leaves no path from Acme to the sanctions list. Replace `sk-your-real-key` with your actual key. The reference project also keeps a `.env.example` with `OPENAI_API_KEY=sk-...` as the placeholder; copy `.env` to `.env.example` and blank out the key if you want the same convention. Keep `.env` out of any version control you add later.

## 5. Add the sample data

Create `data/sample_docs.txt`:

```
Acme Ltd is a UK logistics company. It is owned 60% by Zenith Holdings.

Zenith Holdings is a holding company registered in Cyprus. It is controlled by Bob Petrov.

Bob Petrov was added to the OFAC sanctions list in 2024.

Globex Corp is a shipping company. It is owned 100% by Priya Nair. Priya Nair is a director of Globex Corp.

Acme Ltd has a loan of 5 million GBP with HSBC. The relationship manager for Acme Ltd is Anna Clarke.
```

Notice the sanctions chain: no single paragraph links Acme to OFAC. Globex Corp is a control case with no sanctions link, and the last paragraph adds a loan and a relationship manager for variety.

## Try it

Confirm Neo4j is up and your files are in place:

```bash
docker compose ps
ls data
```

Expected: `kg-neo4j` shown as running with ports `7474` and `7687`, and `sample_docs.txt` listed. In the browser at `http://localhost:7474`, run:

```cypher
RETURN 1
```

You should get a single row with the value `1`.

## Checkpoint

Your project folder should now look like this:

```
kg-app/
├── .env
├── .python-version
├── README.md
├── data/
│   └── sample_docs.txt
├── docker-compose.yml
├── main.py          (uv's placeholder, replaced in Step 6)
├── pyproject.toml
└── uv.lock
```

`docker-compose.yml`, `.env`, and `data/sample_docs.txt` match [../app/docker-compose.yml](../app/docker-compose.yml), [../app/.env.example](../app/.env.example) (apart from the real key), and [../app/data/sample_docs.txt](../app/data/sample_docs.txt) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Cannot resolve address localhost:7687` or connection refused later | Neo4j is still starting or the container is down | Wait 30 seconds, check `docker compose ps` and `docker compose logs neo4j` |
| `docker compose up` fails with "port is already allocated" | Another Neo4j or service is using 7474 or 7687 | Stop the other service, or change the left side of the port mapping and update `NEO4J_URI` |
| Neo4j Browser rejects `neo4j` / `password123` | The volume holds a database created with a different password | `docker compose down -v` to delete the volume, then `docker compose up -d` again |
| `ValueError: Could not use APOC procedures` | Neo4j started without the APOC plugin | Make sure both `NEO4J_PLUGINS` and `NEO4J_dbms_security_procedures_unrestricted` are in `docker-compose.yml`, then `docker compose down && docker compose up -d` |
| Later step says `OPENAI_API_KEY` is missing | `.env` has the placeholder or lives in the wrong folder | `.env` must sit next to `config.py`, and the key must be real |

Next: **[Connections and Config](03-connections-config.md)**.
