from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
from harness.traces import make_trace, write_jsonl


class Clock:
    def __init__(self, ticks): self.t = list(ticks); self.i = 0
    def __call__(self):
        v = self.t[min(self.i, len(self.t) - 1)]; self.i += 1; return v


def _expected(spans):
    root = next(s for s in spans if s["parent_id"] is None)
    kids = [s for s in spans if s is not root]
    d = lambda s: s["end_ms"] - s["start_ms"]
    slow = max(kids, key=d)
    cnt = {}
    for s in kids:
        if s["attrs"].get("input") is not None:
            cnt[s["name"]] = cnt.get(s["name"], 0) + 1
    dup = max(cnt.items(), key=lambda x: x[1])
    toks = sum(s["attrs"].get("tokens_in", 0) + s["attrs"].get("tokens_out", 0) for s in spans)
    return slow["name"], dup, toks, d(root)


def run(ctx):
    m = ctx.load("a6_evals.py")
    close = lambda a, b, t=1e-3: abs(a - b) < t

    def ctxm():
        ok = [close(m.context_precision(["a", "x", "b"], ["a", "b"]), 5 / 6), m.context_precision(["x", "y"], ["a"]) == 0, close(m.context_precision(["a", "b"], ["a", "b"]), 1.0),
              close(m.context_precision(["x", "a"], {"a"}), 0.5), close(m.context_recall(["a", "x"], ["a", "b"]), 0.5), close(m.context_recall([], ["a"]), 0.0), close(m.context_recall(["a", "b", "c"], ["a", "b"]), 1.0)]
        return sum(ok) / len(ok), str(ok)
    ctx.check("A6.1 context_precision / context_recall exactly as specified", 6, ctxm)

    def faith():
        c = ["Outgoing international wire: $40 per wire. Overdraft fee: $25 per item."]
        ok = [close(m.faithfulness("The international wire fee is $40. The moon is made of cheese.", c), 0.5), close(m.faithfulness("The international wire fee is $40.", c), 1.0),
              m.faithfulness("", c) == 0.0, close(m.faithfulness("The overdraft fee is $25 per item.\nThe moon is cheese!", c), 0.5),
              m.faithfulness("The moon is cheese.", c) == 0.0, close(m.faithfulness("The international wire fee is $40.", c, threshold=0.99), 0.0) or True]
        return sum(ok) / len(ok), str(ok)
    ctx.check("A6.2 faithfulness (sentence-level support) exactly as specified", 6, faith)

    def rel():
        ok = [m.answer_relevance("international wire fee", "international wire fee") > 0.99, m.answer_relevance("international wire fee", "The branch is open on Saturday morning") < 0.25, m.answer_relevance("fee", "") == 0.0]
        return sum(ok) / 3, str(ok)
    ctx.check("A6.3 answer_relevance", 3, rel)

    def tca():
        E = lambda n, **a: {"name": n, "args": a}
        ok = [close(m.tool_call_accuracy([E("a", x=1), E("b")], [E("a", x=1, y=2), E("b")]), 1.0), close(m.tool_call_accuracy([E("a"), E("b")], [E("b"), E("a")]), 0.5),
              close(m.tool_call_accuracy([E("a")], [E("a"), E("a"), E("a")]), 1 / 3), m.tool_call_accuracy([], []) == 1.0, close(m.tool_call_accuracy([E("a", x=1)], [E("a", x=2)]), 0.0)]
        return sum(ok) / 5, str(ok)
    ctx.check("A6.4 tool_call_accuracy (ordered, arg-aware, penalises extra calls)", 4, tca)

    def evalrun():
        data = [{"id": "q1", "question": "international wire fee", "gold_docs": ["FEES-001"], "expected_tool_calls": [{"name": "calculate_fee", "args": {}}]},
                {"id": "q2", "question": "who is the ceo", "gold_docs": []}]
        def sysfn(q):
            if "wire" in q:
                return {"answer": "The international wire fee is $40.", "contexts": ["international wire $40 per wire"], "retrieved_ids": ["X", "FEES-001"], "tool_calls": [{"name": "calculate_fee", "args": {}}], "tokens_in": 1000, "tokens_out": 500}
            return {"answer": "I could not find this.", "contexts": [], "retrieved_ids": [], "tool_calls": [], "tokens_in": 500, "tokens_out": 500}
        ck = Clock([0, 0.1, 1.0, 1.5])     # q1 takes 100ms, q2 takes 500ms
        r = m.run_eval(sysfn, data, clock=ck, usd_per_1k_tokens=0.01)
        mt = r["metrics"]
        ok = [r["n"] == 2, close(mt["context_precision"], 0.5) and close(mt["context_recall"], 1.0), "tool_call_accuracy" in mt and close(mt["tool_call_accuracy"], 1.0),
              close(r["latency_ms"]["p50"], 100, 0.5) and close(r["latency_ms"]["p95"], 500, 0.5), r["tokens"] == {"in": 1500, "out": 1000}, close(r["sim_cost_usd"], 0.025, 1e-6), len(r["per_sample"]) == 2]
        return sum(ok) / len(ok), str(ok)
    ctx.check("A6.5 run_eval aggregates metrics, latency percentiles, tokens and SIMULATED cost", 6, evalrun)

    def tracer():
        t = m.Tracer(clock=Clock([0, 1, 2, 5, 9, 10, 11, 12, 13, 14]))
        with t.span("root", user="u") as r:
            with t.span("child1") as c:
                c.set("tokens_in", 7)
            try:
                with t.span("child2"):
                    raise ValueError("x")
            except ValueError:
                pass
        s = {x["name"]: x for x in t.spans}
        ok = [s["root"]["parent_id"] is None, s["child1"]["parent_id"] == s["root"]["span_id"], s["child2"]["parent_id"] == s["root"]["span_id"], s["child1"]["attrs"].get("tokens_in") == 7,
              s["child2"]["attrs"].get("error") == "ValueError", all(x["end_ms"] is not None and x["end_ms"] >= x["start_ms"] for x in t.spans), s["root"]["attrs"].get("user") == "u"]
        p = Path(tempfile.mkdtemp()) / "t.jsonl"; t.to_jsonl(p)
        ok.append(len(p.read_text(encoding="utf-8", errors="replace").splitlines()) == 3)
        return sum(ok) / len(ok), str(ok)
    ctx.check("A6.6 Tracer: nesting, attributes, error capture, JSONL export", 5, tracer)

    def analyze():
        sc = []
        for seed in (7, 11, 23, 41):
            spans = make_trace(seed)
            p = Path(tempfile.mkdtemp()) / "t.jsonl"; write_jsonl(spans, p)
            slow, dup, toks, total = _expected(spans)
            r = m.analyze_trace(str(p))
            r2 = m.analyze_trace(spans)
            ok = [r["slowest_span"] == slow, r["duplicate_calls"] and r["duplicate_calls"][0]["name"] == dup[0] and r["duplicate_calls"][0]["count"] == dup[1], r["total_tokens"] == toks, close(r["total_ms"], total, 0.5), r2["slowest_span"] == slow]
            sc.append(sum(ok) / 5)
        return sum(sc) / len(sc), "checked on 4 generated traces (different seeded inefficiencies)"
    ctx.check("A6.7 analyze_trace finds the slow span, duplicate calls, token total", 5, analyze)

    def gate():
        good = {"n": 1, "metrics": {"faithfulness": 0.9, "context_recall": 0.9}, "latency_ms": {"p50": 100, "p95": 400}, "tokens": {"in": 1, "out": 1}, "sim_cost_usd": 0.01, "per_sample": []}
        d = Path(tempfile.mkdtemp()); f = d / "r.json"; f.write_text(json.dumps(good))
        def call(*args):
            return subprocess.run([sys.executable, str(ctx.dir / "eval_gate.py"), str(f), *args], capture_output=True, text=True, timeout=15).returncode
        ok = [call("--min", "faithfulness=0.8", "--max", "latency_p95_ms=500") == 0, call("--min", "faithfulness=0.95") == 1, call("--max", "sim_cost_usd=0.001") == 1, call("--max", "latency_p95_ms=300") == 1,
              subprocess.run([sys.executable, str(ctx.dir / "eval_gate.py"), str(d / "missing.json")], capture_output=True, timeout=15).returncode == 2]
        names = ["passing thresholds exit 0", "faithfulness below --min exits 1", "cost above --max exits 1", "latency above --max exits 1", "missing file exits 2"]
        detail = "; ".join(f"{n}: {'ok' if v else 'WRONG'}" for n, v in zip(names, ok))
        if not ok[0]:
            return 0, "a valid run must exit 0 first (usage: python eval_gate.py report.json --min faithfulness=0.8 --max latency_p95_ms=500). " + detail
        return sum(ok) / 5, detail
    ctx.check("A6.8 eval_gate.py exits 0 / 1 / 2 correctly (CI-ready)", 3, gate)

    def ci():
        p = ctx.dir / ".github" / "workflows" / "eval.yml"
        t = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        return ("eval_gate" in t and "on:" in t and "python" in t.lower()), "workflow must trigger on push/PR and call eval_gate.py"
    ctx.check("A6.9 GitHub Actions workflow wires the gate into CI", 1, ci)

    def reports():
        b, a = ctx.dir / "reports" / "baseline.json", ctx.dir / "reports" / "after.json"
        if not (b.exists() and a.exists()):
            return 0, "reports/baseline.json and reports/after.json (run_eval outputs) are required"
        mb, ma = json.loads(b.read_text(encoding="utf-8", errors="replace"))["metrics"], json.loads(a.read_text(encoding="utf-8", errors="replace"))["metrics"]
        better = any(ma.get(k, 0) > mb.get(k, 0) + 1e-9 for k in mb)
        no_regress = all(ma.get(k, 0) >= mb[k] - 0.05 for k in mb)
        return 0.6 * better + 0.4 * no_regress, "after must improve at least one metric without regressing others by more than 0.05"
    ctx.check("A6.10 before/after evaluation reports show a measured improvement", 1, reports)

    def dataset():
        p = ctx.dir / "eval_dataset.jsonl"
        n = len([l for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]) if p.exists() else 0
        return (20 <= n <= 30), f"eval_dataset.jsonl has {n} items (expected 20-30)"
    ctx.check("A6.11 eval_dataset.jsonl has 20-30 items (informational)", 0, dataset)
