# Step 7 — Recap and Exercises

> [Back to index](README.md) · Previous: [CLI Entry Point](07-cli-entry-point.md)

## Goal

Consolidate what the app does, list the real failure modes, and give you exercises that push the design further.

## Why this matters

The app is about 110 lines of Python, but it contains the full lifecycle of a graph-backed LLM system: schema design, extraction, entity merging, schema-aware query generation, and an audit trail. The exercises below are chosen because each one forces you to touch a different part of that lifecycle, and most of the real-world difficulty with knowledge graphs lives in exactly those parts.

## Quick reference

| Concept | Where it lives |
| --- | --- |
| Environment-driven LLM and DB connections | `config.py`: `get_llm()`, `get_graph()` |
| Chunking | `ingest.py`: `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)` |
| Fixed schema | `ingest.py`: `ALLOWED_NODES`, `ALLOWED_RELATIONSHIPS` |
| Text to graph extraction | `ingest.py`: `LLMGraphTransformer(...).convert_to_graph_documents(docs)` |
| Writing and provenance | `ingest.py`: `add_graph_documents(..., baseEntityLabel=True, include_source=True)` |
| Wiping the graph | `ingest.py`: `MATCH (n) DETACH DELETE n` behind `reset` |
| Question to Cypher to answer | `query.py`: `GraphCypherQAChain.from_llm(...)` |
| Auditable evidence | `query.py`: `return_intermediate_steps=True`, printed in `ask()` |
| Command-line surface | `main.py`: `ingest` and `ask` subparsers |

## Gotchas

| Gotcha | Why it happens |
| --- | --- |
| Duplicate-looking entities in the graph | `MERGE` matches on exact name; the LLM spelled the same entity two ways |
| Ingest results differ between runs | Extraction is LLM-driven, so counts and occasionally relationships vary |
| `ask` answers from stale data | Ingest is additive; old nodes remain until you use `--reset` |
| Plausible but wrong answers | The generated Cypher is wrong or too loose; always read the printed `Cypher :` line |
| Missing percentages or years | They are only captured if listed in `node_properties` / `relationship_properties` |
| `Could not use APOC procedures` | `Neo4jGraph` needs the APOC plugin enabled in the Neo4j container |
| Multi-hop question answers "I don't know" | The default Cypher prompt writes one-hop queries; `CYPHER_PROMPT` adds variable-length paths |
| Right rows but "I don't know" answer | Bare nodes in the results; `CYPHER_PROMPT` asks for aliased columns and `QA_PROMPT` reads them |
| Wrong edge direction or dropped facts in the graph | A weaker model during extraction; `gpt-4o-mini` did this, `gpt-4o` did not |
| Whole sample file is one chunk | 434 characters fit under the 500-character chunk size; real corpora produce many chunks |
| LLM-generated Cypher can write or delete | `allow_dangerous_requests=True` opts in to this; use a read-only Neo4j user outside demos |

## Discussion questions

1. The chunker produced one chunk for the whole sample file. What would change about extraction quality and cost if each paragraph were its own chunk? What if the chunk size were 5,000?
2. `OWNED_BY` points from the owned company to the owner. What breaks in a query like "who does Zenith own?" if some ingestion runs wrote the edge in the opposite direction?
3. Why does the schema in `ingest.py` make the Cypher the LLM writes in `query.py` more reliable? What would you lose by allowing the extractor free choice of relationship names?
4. The LLM is used for extraction in phase 1 and translation in phase 2. Which phase is more tolerant of a weaker model, and why?
5. `include_source=True` links entities to their source chunk. How would you use that link to give a compliance reviewer a citation for the sanctions answer?

## Exercises

1. **Inspect the graph.** In the Neo4j Browser, run `MATCH (n:__Entity__) RETURN n.id, labels(n)` and confirm every entity has exactly one of your allowed labels plus `__Entity__`.
2. **Add a document.** Append a new paragraph to `data/sample_docs.txt` that ties Globex Corp to a bank, run `ingest` without `--reset`, and confirm the new nodes appear while the old ones do not duplicate.
3. **Extend the schema.** Add a `Country` node type and a `(Company, "REGISTERED_IN", Country)` relationship. Re-ingest with `--reset` and ask "Which companies are registered in Cyprus?" Note that Zenith Holdings is the only one the text mentions.
4. **Read the evidence.** Ask three questions and, for each, copy the printed Cypher into the Neo4j Browser. Then delete `CYPHER_PROMPT` from the chain and ask the sanctions question again; describe in one sentence what changed in the generated Cypher.
5. **Show the RAG failure.** Write a minimal vector-search script (embed the five paragraphs, retrieve top 2 for "Is Acme Ltd exposed to sanctions risk?") and compare what it retrieves against the three-hop path the graph returns. Explain the difference in two sentences.
6. **Rebuild from memory.** Delete `ingest.py` and rewrite it from memory with only the Step 3 and Step 4 goals in front of you, then diff against [../app/ingest.py](../app/ingest.py). Repeat for `query.py` if you want an easy second pass.

## What's next

The natural extensions are in the "Next steps" list of [../notes/WORKFLOW.md](../notes/WORKFLOW.md): a vector index on the chunks combined with the graph (hybrid GraphRAG), entity resolution for aliases, temporal edges, and a read-only Neo4j user for the query chain. For the conceptual background on when to prefer a graph over plain RAG, return to [../notes/knowledge-graph-notes.md](../notes/knowledge-graph-notes.md).
