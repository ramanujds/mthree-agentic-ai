# Step 4 — Ingest: Extraction and Write

> [Back to index](README.md) · Previous: [Ingest: Chunking and Schema](04-ingest-chunking-and-schema.md) · Next: [Query: The Cypher Chain](06-query-cypher-chain.md)

## Goal

Finish `ingest.py`: have the LLM turn each chunk into nodes and relationships that obey the schema, write them to Neo4j, and print a summary. After this step the graph exists.

## Why this matters

`LLMGraphTransformer` is the heart of phase 1. It prompts the LLM with a chunk plus your allowed labels and relationship triples, and parses the reply into `GraphDocument` objects, each holding a list of nodes and a list of relationships. Nothing has touched the database yet at that point; extraction and writing are separate calls, which is useful because you can inspect or filter the result in between.

Writing is where graph ingestion differs from inserting rows. `add_graph_documents` uses `MERGE` semantics: a node is identified by its name and type, so "Zenith Holdings" mentioned in two chunks becomes one node, not two. This is why running ingest twice without a reset does not double the graph, and also why a typo in an entity name ("Zenith Holding") would quietly create a second, disconnected node. Entity resolution is the hard part of graph construction in practice.

Two flags on the write matter. `baseEntityLabel=True` adds a shared `__Entity__` label to every extracted node, which gives you one label to query or index across all types. `include_source=True` also stores each source chunk as a `Document` node and links the entities it produced to it with `MENTIONS`, so any fact can be traced to its original text.

Finally, the `reset` option exists because ingestion is additive. When you change the schema or the extraction settings, stale nodes from the previous run stay behind unless you wipe them first.

## 1. Add the reset option

Change the signature and wipe the graph first when asked. `get_graph` and `get_llm` are imported from `config`, so add that import with the others:

```python
from config import get_graph, get_llm
```

```python
def ingest(path: str = "data/sample_docs.txt", reset: bool = False) -> None:
    graph = get_graph()
    if reset:
        graph.query("MATCH (n) DETACH DELETE n")

    text = Path(path).read_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=c, metadata={"source": path}) for c in splitter.split_text(text)]
```

`MATCH (n) DETACH DELETE n` deletes every node and, via `DETACH`, every relationship attached to it. Cypher refuses to delete a node that still has relationships unless you detach first. Remove the `print` line from Step 3; the final summary replaces it.

## 2. Build the extractor

Import `LLMGraphTransformer` and add the transformer after the chunking lines:

```python
from langchain_experimental.graph_transformers import LLMGraphTransformer
```

```python
    transformer = LLMGraphTransformer(
        llm=get_llm(),
        allowed_nodes=ALLOWED_NODES,
        allowed_relationships=ALLOWED_RELATIONSHIPS,
        node_properties=["percentage"],
        relationship_properties=["percentage", "year"],
    )
    graph_docs = transformer.convert_to_graph_documents(docs)
```

`node_properties` and `relationship_properties` tell the extractor which extra facts to capture beyond names and links. This is how "owned 60%" can become a `percentage` property and "added to the sanctions list in 2024" can become a `year`. Without them, those numbers are dropped, because the schema only allows structure.

`convert_to_graph_documents` is where the LLM calls happen, one per chunk. This is the slow, paid part of the app.

## 3. Write to Neo4j and refresh the schema

```python
    graph.add_graph_documents(graph_docs, baseEntityLabel=True, include_source=True)
    graph.refresh_schema()
```

`refresh_schema()` re-reads the database's labels and relationship types into the `graph` object. Phase 2 builds its own connection, so this call is not strictly needed for `ask`, but it keeps this connection's cached schema in sync with what was just written.

## 4. Print a summary

```python
    n_nodes = sum(len(g.nodes) for g in graph_docs)
    n_rels = sum(len(g.relationships) for g in graph_docs)
    print(f"Ingested {len(docs)} chunks -> {n_nodes} nodes, {n_rels} relationships")
```

These counts are what the LLM *extracted*, before merging duplicates in Neo4j, so they can be larger than the node count you later see in the database.

## Try it

```bash
uv run python -c "from ingest import ingest; ingest(reset=True)"
```

Expected output (exact numbers vary from run to run because the extraction is LLM-driven):

```
Ingested 1 chunks -> 8 nodes, 7 relationships
```

With `gpt-4o`, the 8 nodes are Acme Ltd, Zenith Holdings, Bob Petrov, the OFAC list, Globex Corp, Priya Nair, HSBC and Anna Clarke, and the 7 relationships are one per fact in the sample file. Now look at the result in the Neo4j Browser at `http://localhost:7474`:

```cypher
MATCH (n)-[r]->(m) RETURN n, r, m
```

The exact rows should be (names are title-cased by the extractor, so you will see `Hsbc` and `Ofac Sanctions List`):

| From | Relationship | To |
| --- | --- | --- |
| Acme Ltd | OWNED_BY (percentage 60%) | Zenith Holdings |
| Zenith Holdings | CONTROLLED_BY | Bob Petrov |
| Bob Petrov | ON_LIST (year 2024) | Ofac Sanctions List |
| Globex Corp | OWNED_BY (percentage 100%) | Priya Nair |
| Priya Nair | DIRECTOR_OF | Globex Corp |
| Acme Ltd | HAS_LOAN_WITH | Hsbc |
| Acme Ltd | MANAGED_BY | Anna Clarke |

In words: you should see Acme Ltd pointing to Zenith Holdings, Zenith to Bob Petrov, Bob to a sanctions list node, Globex Corp to Priya Nair, and so on, plus `MENTIONS` edges from the source `Document` node. If the Acme to Zenith to Bob to OFAC path is missing a link, the question in Step 5 will fail for the right reason: the data was never extracted.

Run it a second time without `reset` and re-run the Cypher above. The visible nodes should not double.

## Checkpoint

<details>
<summary>Full <code>ingest.py</code></summary>

```python
"""Step 1: text -> chunks -> LLM extracts entities/relations -> Neo4j."""
from pathlib import Path

from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_graph, get_llm

# Constrain the schema so the LLM produces a clean, consistent graph.
ALLOWED_NODES = ["Person", "Company", "SanctionList", "Loan", "Bank"]
ALLOWED_RELATIONSHIPS = [
    ("Company", "OWNED_BY", "Company"),
    ("Company", "OWNED_BY", "Person"),
    ("Company", "CONTROLLED_BY", "Person"),
    ("Person", "DIRECTOR_OF", "Company"),
    ("Person", "ON_LIST", "SanctionList"),
    ("Company", "HAS_LOAN_WITH", "Bank"),
    ("Company", "MANAGED_BY", "Person"),
]


def ingest(path: str = "data/sample_docs.txt", reset: bool = False) -> None:
    graph = get_graph()
    if reset:
        graph.query("MATCH (n) DETACH DELETE n")

    text = Path(path).read_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=c, metadata={"source": path}) for c in splitter.split_text(text)]

    transformer = LLMGraphTransformer(
        llm=get_llm(),
        allowed_nodes=ALLOWED_NODES,
        allowed_relationships=ALLOWED_RELATIONSHIPS,
        node_properties=["percentage"],
        relationship_properties=["percentage", "year"],
    )
    graph_docs = transformer.convert_to_graph_documents(docs)
    graph.add_graph_documents(graph_docs, baseEntityLabel=True, include_source=True)
    graph.refresh_schema()

    n_nodes = sum(len(g.nodes) for g in graph_docs)
    n_rels = sum(len(g.relationships) for g in graph_docs)
    print(f"Ingested {len(docs)} chunks -> {n_nodes} nodes, {n_rels} relationships")
```

</details>

This matches [../app/ingest.py](../app/ingest.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Fewer relationships than expected (for example 5 instead of 7) and the ownership edge points from Zenith to Acme | A small model such as `gpt-4o-mini` dropped facts and reversed `OWNED_BY` | Use `LLM_MODEL=gpt-4o`; always compare the Browser graph against the table above before moving on |
| `Ingested 1 chunks -> 0 nodes, 0 relationships` | The LLM returned nothing usable, often a weak model or a rate-limit retry | Re-run; try a stronger model via `LLM_MODEL` in `.env` |
| Graph has `Zenith Holdings` and `Zenith Holding` as separate nodes | `MERGE` matches on exact name, and the LLM spelled it two ways | Re-run with `reset=True`; for real data, add an entity-resolution pass after extraction |
| Old nodes from earlier experiments pollute answers | Ingest is additive | Pass `--reset` (Step 6) or run `MATCH (n) DETACH DELETE n` in the Browser |
| Percentages and years are missing from the graph | `node_properties` / `relationship_properties` left out | Keep the two property lists in the `LLMGraphTransformer` call |

Next: **[Query: The Cypher Chain](06-query-cypher-chain.md)**.
