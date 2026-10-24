"""A simple always-available BM25 retriever so that Weeks 4-8 do not depend on your own Week-2 code."""
from __future__ import annotations
from . import CORPUS_DIR, faults
from .corpus import load_corpus
from .text import BM25, tokenize


class BaselineRetriever:
    def __init__(self, corpus_dir=CORPUS_DIR):
        self.chunks = []
        for d in load_corpus(corpus_dir):
            if d.status == "superseded":
                continue
            for h, body in d.sections:
                if body:
                    self.chunks.append({"doc_id": d.doc_id, "chunk_id": f"{d.doc_id}#{h or 'intro'}",
                                        "text": f"{d.title} - {h}: {body}"})
        self.bm25 = BM25().fit([tokenize(c["text"]) for c in self.chunks])
        self.calls = 0

    def __call__(self, query: str, k: int = 5) -> list[dict]:
        self.calls += 1
        sc = self.bm25.scores(tokenize(query))
        order = sorted(range(len(sc)), key=lambda i: -sc[i])[:k]
        hits = [dict(self.chunks[i], score=round(sc[i], 4)) for i in order]
        return faults.degrade_hits(hits)
