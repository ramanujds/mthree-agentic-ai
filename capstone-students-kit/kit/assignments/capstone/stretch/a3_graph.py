"""Stretch S1a - knowledge graph + GraphRAG (use networkx; Neo4j is optional and not required).

extract_triples(text, doc_id, llm, max_retries=2) -> {"entities": [{"name","type","aliases"}], "triples": [{"head","relation","tail"}]}
    * Build a prompt for `llm.complete(prompt)` (see harness.llm.MockExtractionLLM). The prompt MUST contain a line "DOC_ID: <doc_id>".
    * The model's output is messy: prose around the JSON, ```json fences, sometimes truncated/invalid JSON. Parse defensively,
      VALIDATE with Pydantic, and retry up to max_retries times on invalid output.
    * If every attempt fails, return {"entities": [], "triples": [], "error": "<reason>"} - never raise.

build_graph(corpus_dir, llm) -> networkx.DiGraph or MultiDiGraph
    * one node per real-world entity: nodes are keyed by CANONICAL name (resolve aliases such as 'T. Weber' -> 'Tomas Weber')
    * node attrs: type, aliases(list); edge attrs: relation, source_doc. Do not create duplicate edges.

graph_retrieve(graph, question, hops=3) -> list[{"head","relation","tail","source_doc"}]
    * link entities mentioned in the question (canonical names AND aliases, case-insensitive), expand `hops` hops in BOTH directions,
      return the evidence triples. Return [] when the question mentions no known entity.
"""
from __future__ import annotations


def extract_triples(text, doc_id, llm, max_retries=2):
    raise NotImplementedError("capstone: extract_triples")


def build_graph(corpus_dir, llm):
    raise NotImplementedError("capstone: build_graph")


def graph_retrieve(graph, question, hops=3):
    raise NotImplementedError("capstone: graph_retrieve")
