"""Capstone R1 - RAG pipeline (pure Python; you may use LlamaIndex components inside if you wish, but the contract below is what is graded).

build_index(corpus_dir, chunking="section", chunk_size=60, overlap=10, embedder=None) -> index
    chunking   : "fixed" (sliding window of `chunk_size` WORDS with `overlap`), "section" (one chunk per '## ' section), or "semantic"
                 (group adjacent sentences while they stay topically similar; never exceed chunk_size words)
    embedder   : default harness.text.HashingEmbedder()  (free, offline). You may also use sentence-transformers locally if installed.
    Every chunk must keep metadata: doc_id, chunk_id, status ("current"/"superseded") - parse the front matter (harness.corpus.load_corpus does it).

retrieve(index, query, k=5, mode="hybrid", rerank=False, exclude_superseded=True) -> list[dict]
    mode : "bm25" | "dense" | "hybrid" (BM25 + dense fused, e.g. Reciprocal Rank Fusion harness.text.rrf)
    each hit: {"doc_id": str, "chunk_id": str, "text": str, "score": float}, best first, at most k hits
    exclude_superseded=True must hide chunks of superseded documents (stale-index failure mode); False must return them.

answer(index, query, llm=None, k=4) -> {"answer": str, "sources": [doc_id, ...], "abstained": bool}
    Must ABSTAIN (abstained=True, empty sources, say it cannot find the answer) when the corpus does not contain the answer.

Document your chunking and retrieval choices, with the numbers that justify them, in README.md and docs/architecture.md (the trainer reads them;
the evidence gate checks README.md has at least 200 words). Comparing two or more strategies on your own dataset is a good way to get those numbers.
"""
from __future__ import annotations


def build_index(corpus_dir, chunking="section", chunk_size=60, overlap=10, embedder=None):
    raise NotImplementedError("capstone R1: build_index")


def retrieve(index, query, k=5, mode="hybrid", rerank=False, exclude_superseded=True):
    raise NotImplementedError("capstone R1: retrieve")


def answer(index, query, llm=None, k=4):
    raise NotImplementedError("capstone R1: answer")
