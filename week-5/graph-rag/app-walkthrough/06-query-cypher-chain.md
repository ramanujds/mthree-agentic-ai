# Step 5 — Query: The Cypher Chain

> [Back to index](README.md) · Previous: [Ingest: Extraction and Write](05-ingest-extraction-and-write.md) · Next: [CLI Entry Point](07-cli-entry-point.md)

## Goal

Build `query.py`: take an English question, have the LLM write Cypher against the graph, run it, and return a natural-language answer, while printing the Cypher and the raw rows so the answer is auditable.

## Why this matters

`GraphCypherQAChain` runs three stages. First it sends your question plus the graph's *schema* (the labels, relationship types, and properties that Neo4j reported) to the LLM and asks for a Cypher query. Then it executes that query. Then it sends the question and the returned rows back to the LLM to phrase the final answer. The graph does the multi-hop reasoning; the LLM only translates at either end.

That structure is why the schema in Step 3 mattered. The LLM can only write a good `MATCH` if the schema it sees uses consistent names.

`return_intermediate_steps=True` is the feature that makes graph QA defensible. The result carries the generated Cypher and the rows it returned, and `ask()` prints both. When an answer is wrong you can tell immediately whether the model wrote bad Cypher or Cypher was fine but the graph lacked the data. Compare that with a vector-search pipeline, where "why did it retrieve this chunk" has no inspectable answer.

The default chain works for simple lookups but not for the question this whole app exists for. Left alone, the model writes a one-hop query such as `(Acme)-[:ON_LIST]->(...)`, gets zero rows, and answers "I don't know". Nothing is wrong with the graph; the model just did not realise that ownership chains are variable-length. So the two sub-steps below add two prompts that fix the two places the default chain goes wrong: how Cypher is written, and how rows are turned into an answer.

The one thing to be careful about is `allow_dangerous_requests=True`. LangChain requires you to opt in because the chain executes whatever Cypher the LLM produces, including writes or deletes if the model were manipulated by a malicious question. For a local demo that is fine. In production, connect with a **read-only** Neo4j user.

## 1. Build the default chain

Create `query.py`:

```python
"""Step 2: question -> LLM writes Cypher -> Neo4j runs it -> LLM answers."""
from langchain_neo4j import GraphCypherQAChain

from config import get_graph, get_llm


def build_chain() -> GraphCypherQAChain:
    return GraphCypherQAChain.from_llm(
        llm=get_llm(),
        graph=get_graph(),
        verbose=True,
        return_intermediate_steps=True,
        allow_dangerous_requests=True,  # LLM-generated Cypher; use a read-only DB user in prod
    )
```

`verbose=True` makes LangChain print the generated Cypher and the full context as it runs, which is the live-demo view. The `Step 2` in the docstring means phase 2 of the app, as in [../notes/WORKFLOW.md](../notes/WORKFLOW.md). Add the `ask()` function at the bottom:

```python
def ask(question: str) -> str:
    result = build_chain().invoke({"query": question})
    steps = result["intermediate_steps"]
    print("\nCypher :", steps[0]["query"])
    print("Context:", steps[1]["context"])
    return result["result"]
```

The chain's input key is `query`, not `question`. `intermediate_steps` is a list: the first item holds the generated Cypher under `query`, and the second holds the rows Neo4j returned under `context`. The final English answer is under `result`.

Try it now, with the default prompts:

```bash
uv run python -c "from query import ask; print(ask('Is Acme Ltd exposed to sanctions risk?'))"
```

On a healthy graph this fails. The model writes a Cypher query that looks for an `ON_LIST` edge directly on Acme Ltd, `Context:` is `[]`, and the answer is `I don't know the answer.` Keep that output in mind; the next two sub-steps fix it.

## 2. Teach the model to write multi-hop Cypher

Add the import `from langchain_core.prompts import PromptTemplate` and a `CYPHER_PROMPT` above `build_chain()`:

```python
CYPHER_PROMPT = PromptTemplate.from_template(
    """Task: write one Cypher query that answers the question.

Schema:
{schema}

Rules:
- Use only the labels and relationship types in the schema.
- Entities are matched by their `id` property, e.g. (c:Company {{id: 'Acme Ltd'}}).
- Ownership and control chains can be several hops deep. Follow them with a
  variable-length path, e.g. (c)-[:OWNED_BY|CONTROLLED_BY*1..4]->(x).
- Return readable columns with aliases that include the entity named in the
  question, e.g. RETURN c.id AS company, p.id AS manager, instead of bare nodes.
- Return only the Cypher query, with no explanation and no code fences.

Example question: Is Globex Corp connected to a sanctioned person?
Example query:
MATCH p = (c:Company {{id: 'Globex Corp'}})-[:OWNED_BY|CONTROLLED_BY*1..4]->(x)-[:ON_LIST]->(l)
RETURN p

Question: {question}
Cypher query:"""
)
```

Each rule fixes something observed in practice:

| Rule | Failure it prevents |
| --- | --- |
| Use only labels and relationship types in the schema | Invented edge names that match nothing |
| Match entities by `id` | `name` or `title` properties that do not exist on these nodes |
| Variable-length path `*1..4` | One-hop queries that cannot cross Acme, Zenith, Bob, and OFAC |
| Return readable aliased columns | Bare nodes like `{'p': {'id': 'Anna Clarke'}}` that the answering LLM cannot connect to the question |
| Return only Cypher | Prose or code fences that Neo4j rejects |

In the prompt text, every literal curly brace in the Cypher example is doubled (`{{id: ...}}`) because `PromptTemplate` treats single braces as template variables. Only `{schema}` and `{question}` are real variables.

## 3. Teach the model to read the rows

Add `QA_PROMPT` below `CYPHER_PROMPT`:

```python
QA_PROMPT = PromptTemplate.from_template(
    """Answer the question using only the query results below.
Each result row is evidence from the knowledge graph. If a row holds a path,
explain the chain of relationships step by step. Say you don't know only if
the results are empty.

Query results:
{context}

Question: {question}
Answer:"""
)
```

The default answering prompt tends to say "I don't know" even when it was given rows, if the rows look like bare nodes. This one tells the model that every row is evidence, that paths should be explained hop by hop, and that "I don't know" is reserved for genuinely empty results.

## 4. Wire both prompts into the chain

Pass them to `from_llm`:

```python
def build_chain() -> GraphCypherQAChain:
    return GraphCypherQAChain.from_llm(
        llm=get_llm(),
        graph=get_graph(),
        cypher_prompt=CYPHER_PROMPT,
        qa_prompt=QA_PROMPT,
        verbose=True,
        return_intermediate_steps=True,
        allow_dangerous_requests=True,  # LLM-generated Cypher; use a read-only DB user in prod
    )
```

## Try it

Make sure you ran ingest in Step 4, then:

```bash
uv run python -c "from query import ask; print(ask('Is Acme Ltd exposed to sanctions risk?'))"
```

Expected output (the exact Cypher and wording vary from run to run; the shape is stable):

```
Cypher : MATCH p = (c:Company {id: 'Acme Ltd'})-[:OWNED_BY|CONTROLLED_BY*1..4]->(x)-[:ON_LIST]->(l)
RETURN c.id AS company, ...
Context: [{'company': 'Acme Ltd', 'sanctionlist': 'Ofac Sanctions List', 'entity_connected_to_sanctionlist': 'Bob Petrov'}]
Yes, Acme Ltd is exposed to sanctions risk. ... Bob Petrov, who is connected to Acme Ltd, is on the Ofac Sanctions List. ...
```

The thing to check is that the Cypher follows `OWNED_BY` and `CONTROLLED_BY` edges out from Acme and ends at an `ON_LIST` edge. Then try simple lookups:

```bash
uv run python -c "from query import ask; print(ask('Who manages Acme Ltd?'))"
```

Expected: `Acme Ltd is managed by Anna Clarke.`

## Checkpoint

<details>
<summary>Full <code>query.py</code></summary>

```python
"""Step 2: question -> LLM writes Cypher -> Neo4j runs it -> LLM answers."""
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain

from config import get_graph, get_llm

CYPHER_PROMPT = PromptTemplate.from_template(
    """Task: write one Cypher query that answers the question.

Schema:
{schema}

Rules:
- Use only the labels and relationship types in the schema.
- Entities are matched by their `id` property, e.g. (c:Company {{id: 'Acme Ltd'}}).
- Ownership and control chains can be several hops deep. Follow them with a
  variable-length path, e.g. (c)-[:OWNED_BY|CONTROLLED_BY*1..4]->(x).
- Return readable columns with aliases that include the entity named in the
  question, e.g. RETURN c.id AS company, p.id AS manager, instead of bare nodes.
- Return only the Cypher query, with no explanation and no code fences.

Example question: Is Globex Corp connected to a sanctioned person?
Example query:
MATCH p = (c:Company {{id: 'Globex Corp'}})-[:OWNED_BY|CONTROLLED_BY*1..4]->(x)-[:ON_LIST]->(l)
RETURN p

Question: {question}
Cypher query:"""
)

QA_PROMPT = PromptTemplate.from_template(
    """Answer the question using only the query results below.
Each result row is evidence from the knowledge graph. If a row holds a path,
explain the chain of relationships step by step. Say you don't know only if
the results are empty.

Query results:
{context}

Question: {question}
Answer:"""
)


def build_chain() -> GraphCypherQAChain:
    return GraphCypherQAChain.from_llm(
        llm=get_llm(),
        graph=get_graph(),
        cypher_prompt=CYPHER_PROMPT,
        qa_prompt=QA_PROMPT,
        verbose=True,
        return_intermediate_steps=True,
        allow_dangerous_requests=True,  # LLM-generated Cypher; use a read-only DB user in prod
    )


def ask(question: str) -> str:
    result = build_chain().invoke({"query": question})
    steps = result["intermediate_steps"]
    print("\nCypher :", steps[0]["query"])
    print("Context:", steps[1]["context"])
    return result["result"]
```

</details>

This matches [../app/query.py](../app/query.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: ... allow_dangerous_requests` | The opt-in flag was left out | Pass `allow_dangerous_requests=True` (and understand why, per the section above) |
| `I don't know the answer.` and `Context: []` | The generated Cypher matched nothing: wrong direction, one hop instead of several, or the data was never ingested | Read the printed `Cypher :` line, paste it into the Neo4j Browser, and compare with the graph from Step 4 |
| Correct rows in `Context:` but the answer still says "I don't know" | The rows are bare nodes the answering model cannot tie to the question, or `QA_PROMPT` is not wired in | Keep the "readable columns" rule in `CYPHER_PROMPT` and pass `qa_prompt=QA_PROMPT` |
| `KeyError: 'intermediate_steps'` | `return_intermediate_steps=True` missing | Add it to `from_llm` |
| `KeyError` or `Missing some input keys` building the prompt | A literal `{` or `}` in the Cypher example was not doubled | Double every brace that is not `{schema}` or `{question}` |

Next: **[CLI Entry Point](07-cli-entry-point.md)**.
