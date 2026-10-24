from __future__ import annotations
import json
from harness import CORPUS_DIR, DATA_DIR
from .framework import read_jsonl


def _questions(ctx):
    qs = read_jsonl(DATA_DIR / "eval_public.jsonl")
    if ctx.has_holdout and (ctx.holdout / "eval_holdout.jsonl").exists():
        qs += read_jsonl(ctx.holdout / "eval_holdout.jsonl")
    return qs


def _recall(m, ix, qs, **kw):
    sc = []
    for q in qs:
        ids = {h["doc_id"] for h in m.retrieve(ix, q["question"], **kw)}
        sc.append(len(ids & set(q["gold_docs"])) / len(q["gold_docs"]))
    return sum(sc) / len(sc)


def run(ctx):
    m = ctx.load("a2_rag.py")
    qs = _questions(ctx)
    ans = [q for q in qs if q["gold_docs"]]
    unans = [q for q in qs if not q["gold_docs"]]
    cache = {}

    def ix(chunking="section", **kw):
        key = (chunking, tuple(sorted(kw.items())))
        if key not in cache:
            cache[key] = m.build_index(str(CORPUS_DIR), chunking=chunking, **kw)
        return cache[key]

    def shape():
        hits = m.retrieve(ix(), "international wire fee", k=3)
        ok = len(hits) <= 3 and hits and all({"doc_id", "chunk_id", "text", "score"} <= set(h) for h in hits)
        ok = ok and hits[0]["score"] >= hits[-1]["score"]
        return bool(ok), "hits need doc_id/chunk_id/text/score, best first, <= k"
    ctx.check("A2.1 retrieve() returns well-formed hits", 4, shape)

    def chunkings():
        sizes = {}
        for c in ("fixed", "section", "semantic"):
            h = m.retrieve(ix(c, chunk_size=40, overlap=8), "monthly fee Everyday Saver waived", k=5)
            sizes[c] = max(len(x["text"].split()) for x in h)
        return (sizes["fixed"] <= 40 + 12) * 0.5 + (sizes["semantic"] <= 40 + 12) * 0.3 + 0.2, f"max words per chunk (limit 40+title): {sizes}"
    ctx.check("A2.2 three chunking strategies; chunk_size respected", 6, chunkings)

    def modes():
        r = {md: _recall(m, ix(), ans, k=5, mode=md) for md in ("bm25", "dense", "hybrid")}
        return (min(r["bm25"] / 0.6, 1) + min(r["dense"] / 0.5, 1) + min(r["hybrid"] / 0.75, 1)) / 3, f"recall@5 {r} (targets bm25>=.60 dense>=.50 hybrid>=.75)"
    ctx.check("A2.3 retrieval quality: BM25 / dense / hybrid recall@5", 10, modes)

    def stale():
        st = [q for q in qs if q["type"] == "stale_trap"]
        top1_ok = sum(m.retrieve(ix(), q["question"], k=3)[0]["doc_id"] not in q["forbidden_top1"] for q in st) / len(st)
        shows = any(h["doc_id"] == "FEES-000" for h in m.retrieve(ix(), "overdraft fee per item", k=10, exclude_superseded=False))
        return 0.75 * top1_ok + 0.25 * shows, f"stale-free top-1 {top1_ok:.2f}; flag really toggles superseded docs: {shows}"
    ctx.check("A2.4 avoids stale (superseded) documents; metadata filter works", 6, stale)

    def rer():
        base = _recall(m, ix(), ans, k=3, mode="hybrid", rerank=False)
        rr = _recall(m, ix(), ans, k=3, mode="hybrid", rerank=True)
        return (rr >= base - 0.02 and rr >= 0.6), f"recall@3 without rerank {base:.2f}, with rerank {rr:.2f} (rerank must not hurt and be >= .60)"
    ctx.check("A2.5 reranking option works and does not degrade results", 4, rer)

    def abstain():
        a_ok = sum(not m.answer(ix(), q["question"])["abstained"] for q in ans) / len(ans)
        u = [m.answer(ix(), q["question"]) for q in unans]
        u_ok = sum(x["abstained"] and not x["sources"] for x in u) / len(u)
        return 0.4 * min(a_ok / 0.85, 1) + 0.6 * min(u_ok / 0.66, 1), f"answers when it should {a_ok:.2f}; abstains when it should {u_ok:.2f} (full marks at >= 2 of 3; the CEO question is a deliberate hard negative - the entity exists but the fact does not)"
    ctx.check("A2.6 answers when supported, abstains when not", 6, abstain)

    def grounded():
        good = 0
        for q in ans:
            r = m.answer(ix(), q["question"])
            good += bool(set(r["sources"]) & set(q["gold_docs"])) and not r["abstained"]
        return good / len(ans) / 0.8, f"{good}/{len(ans)} answers cite at least one gold document"
    ctx.check("A2.7 answers cite correct sources", 4, grounded)

    def docs():
        rd, rp = ctx.dir / "README.md", ctx.dir / "reports" / "a2_chunking_results.json"
        t = rd.read_text(encoding="utf-8", errors="replace").lower() if rd.exists() else ""
        sec = sum(h in t for h in ("chunking", "retrieval", "trade-off")) / 3
        words = min(len(t.split()) / 250, 1)
        rep = 0
        if rp.exists():
            try:
                d = json.loads(rp.read_text(encoding="utf-8", errors="replace")); rep = 1 if isinstance(d, list) and len(d) >= 2 and all("strategy" in x and "recall_at_5" in x for x in d) else 0.3
            except Exception:
                rep = 0
        return (sec + words + rep) / 3, f"README sections {sec:.2f}, length {words:.2f}, results file {rep}"
    ctx.check("A2.8 README + chunking experiment results present", 0, docs)    # informational; scored by trainer rubric
