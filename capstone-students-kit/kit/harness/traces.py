"""Seeded trace generator for Assignment 6 (find the injected inefficiency)."""
from __future__ import annotations
import json, random


def make_trace(seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    spans, t, tid = [], 0.0, f"trace-{seed:04d}"
    root = {"trace_id": tid, "span_id": "s0", "parent_id": None, "name": "agent.run", "start_ms": 0.0, "end_ms": 0.0, "attrs": {"user": "u1"}}
    spans.append(root)

    def add(name, dur, attrs=None):
        nonlocal t
        sid = f"s{len(spans)}"
        spans.append({"trace_id": tid, "span_id": sid, "parent_id": "s0", "name": name, "start_ms": round(t, 1), "end_ms": round(t + dur, 1), "attrs": attrs or {}})
        t += dur

    slow = rng.choice(["rerank", "tool.calculate_fee", "llm.answer"])
    dup = rng.choice(["retrieve", "tool.lookup_account_status"])
    n_dup = rng.randint(4, 7)
    add("llm.plan", rng.randint(500, 800), {"tokens_in": 420, "tokens_out": 60})
    for _ in range(n_dup):
        add(dup, rng.randint(250, 450), {"input": "wire fee international"})
    add("tool.calculate_fee" if slow != "tool.calculate_fee" else slow, rng.randint(40, 90) if slow != "tool.calculate_fee" else rng.randint(3000, 5000), {"input": "international_wire"})
    add("rerank", rng.randint(150, 300) if slow != "rerank" else rng.randint(3000, 5000), {"input": "top20"})
    add("llm.answer", rng.randint(600, 900) if slow != "llm.answer" else rng.randint(3000, 5000), {"tokens_in": 900 + 80 * n_dup, "tokens_out": 120})
    root["end_ms"] = round(t, 1)
    return spans


def write_jsonl(spans, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in spans:
            f.write(json.dumps(s) + "\n")


if __name__ == "__main__":
    write_jsonl(make_trace(7), "data/traces/seeded_trace.jsonl")
