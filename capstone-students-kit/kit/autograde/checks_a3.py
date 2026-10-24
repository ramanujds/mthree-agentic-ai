from __future__ import annotations
import json
from harness import CORPUS_DIR, DATA_DIR
from harness.llm import MockExtractionLLM
from harness.text import count_tokens, extractive_summary
from .framework import read_jsonl

ORACLE = json.loads((DATA_DIR / "extraction_oracle.json").read_text(encoding="utf-8", errors="replace"))


def _expected_nodes():
    s = set()
    for d in ORACLE.values():
        s |= {e["name"] for e in d["entities"]}
        for t in d["triples"]:
            s |= {t["head"], t["tail"]}
    return s


def run(ctx):
    g = ctx.load("a3_graph.py")
    mem = ctx.load("a3_memory.py")

    def extraction():
        score, notes = 0, []
        for doc_id, d in ORACLE.items():
            m = MockExtractionLLM()
            r = g.extract_triples("text", doc_id, m)
            ok = len(r["triples"]) == len(d["triples"]) and "error" not in r
            score += ok
            if not ok:
                notes.append(doc_id)
        return score / len(ORACLE), f"failed for {notes}" if notes else ""
    ctx.check("A3.1 extract_triples copes with messy / truncated model output (retries + validation)", 6, extraction)

    def garbage():
        class Bad:
            def complete(self, p): return "sorry, I cannot do that {not json"
        r = g.extract_triples("x", "ORG-001", Bad(), max_retries=2)
        ok = r.get("entities") == [] and r.get("triples") == [] and r.get("error")
        calls = []
        class Count:
            def complete(self, p): calls.append(1); return "nope"
        g.extract_triples("x", "ORG-001", Count(), max_retries=2)
        return (0.6 if ok else 0) + (0.4 if len(calls) == 3 else 0), f"returned {r}; attempts={len(calls)} (expected 3 = 1 + 2 retries)"
    ctx.check("A3.2 total failure is returned as a structured error, never raised; retry count honoured", 3, garbage)

    graph = {}
    def build():
        gr = g.build_graph(str(CORPUS_DIR), MockExtractionLLM())
        graph["g"] = gr
        exp = _expected_nodes()
        nodes = set(gr.nodes)
        aliases = {a for d in ORACLE.values() for e in d["entities"] for a in e["aliases"]}
        alias_nodes = nodes & aliases
        edges = {(u, d["relation"], v) for u, v, d in gr.edges(data=True)}
        want = {(t["head"], t["relation"], t["tail"]) for d in ORACLE.values() for t in d["triples"]}
        # aliases in triples are resolved to canonical via the entity lists, so compare after mapping
        frac_nodes = 1 - min(1, len(nodes ^ exp) / len(exp))
        return (0.5 * frac_nodes + 0.3 * (not alias_nodes) + 0.2 * (len(edges & want) / len(want))), \
               f"nodes {len(nodes)}/{len(exp)} expected; alias nodes left: {sorted(alias_nodes)}; triples matched {len(edges & want)}/{len(want)}"
    ctx.check("A3.3 build_graph: entity resolution, no alias duplicates, no duplicate edges", 8, build)

    def attrs():
        gr = graph["g"]
        e = list(gr.edges(data=True))
        return all("relation" in d and "source_doc" in d for _, _, d in e) and gr.nodes["Tomas Weber"].get("type") == "Person" and len(e) == len({(u, d["relation"], v) for u, v, d in e})
    ctx.check("A3.4 node/edge attributes (type, relation, source_doc); no duplicate edges", 2, attrs)

    def multi():
        qs = read_jsonl(DATA_DIR / "graph_eval_public.jsonl")
        if ctx.has_holdout and (ctx.holdout / "graph_eval_holdout.jsonl").exists():
            qs += read_jsonl(ctx.holdout / "graph_eval_holdout.jsonl")
        sc, miss = 0, []
        for q in qs:
            ev = " ".join(f"{t['head']} {t['relation']} {t['tail']}" for t in g.graph_retrieve(graph["g"], q["question"]))
            f = sum(a in ev for a in q["answer_entities"]) / len(q["answer_entities"])
            sc += f
            if f < 1:
                miss.append(q["id"])
        return sc / len(qs), f"missing answer entities in evidence for {miss}"
    ctx.check("A3.5 graph_retrieve finds the evidence for multi-hop questions", 7, multi)

    def linking():
        gr = graph["g"]
        a = "Tomas Weber" in " ".join(f"{t['head']} {t['tail']}" for t in g.graph_retrieve(gr, "Who directs the Harbor St branch?"))
        b = g.graph_retrieve(gr, "What is the weather today?") == []
        return 0.6 * a + 0.4 * b, f"alias linking ok={a}; empty when no entity ok={b}"
    ctx.check("A3.6 entity linking handles aliases; returns [] when nothing is linked", 2, linking)

    # ---- memory ----
    calls = []
    def summ(msgs):
        calls.append(msgs)
        return extractive_summary(msgs)
    def mkmem(n=40, budget=200):
        calls.clear()
        m = mem.ConversationMemory(budget, summ)
        m.pin("account_id", "ACC-1002")
        for i in range(n):
            m.add("user" if i % 2 == 0 else "assistant", f"Turn {i}. This is a fairly long message number {i} about wire transfers and account questions for the customer.")
        return m

    def budget():
        m = mkmem()
        ctxm = m.get_context()
        tokens = sum(count_tokens(x["content"]) for x in ctxm)
        ok_b = tokens <= 200
        last = ctxm[-1]["content"].startswith("Turn 39")
        order = [x["content"] for x in ctxm[1:]]
        in_order = order == sorted(order, key=lambda s: int(s.split(".")[0].split()[1]))
        return (0.4 * ok_b + 0.3 * last + 0.3 * in_order), f"tokens={tokens} (<=200), last turn kept={last}, order kept={in_order}"
    ctx.check("A3.7 memory: stays within token budget, keeps the newest turns in order", 4, budget)

    def pins():
        m = mkmem()
        c = m.get_context()
        return c[0]["role"] == "system" and "ACC-1002" in c[0]["content"]
    ctx.check("A3.8 memory: pinned facts always survive", 2, pins)

    def summary():
        m = mkmem()
        c = m.get_context()
        txt = c[0]["content"].lower()
        dropped_first = bool(calls) and any("Turn 0" in x["content"] for x in calls[0])
        return (0.5 * ("summary" in txt) + 0.5 * dropped_first), "context must include a summary of dropped turns, built from the oldest turns"
    ctx.check("A3.9 memory: older turns are summarised, not just discarded", 3, summary)

    def efficient():
        m = mkmem()
        m.get_context(); n1 = len(calls); m.get_context(); n2 = len(calls)
        return (n1 <= 20 and n2 == n1), f"summarizer calls={n1} (<=20), extra calls on repeat get_context={n2 - n1} (must be 0)"
    ctx.check("A3.10 memory: summariser is not called needlessly", 3, efficient)

    def design():
        p = ctx.dir / "memory_design.md"
        t = p.read_text(encoding="utf-8", errors="replace").lower() if p.exists() else ""
        return sum(k in t for k in ("short-term", "long-term", "episodic", "semantic", "privacy", "retention")) / 6, f"{len(t.split())} words"
    ctx.check("A3.11 memory_design.md covers key concepts", 0, design)   # informational
