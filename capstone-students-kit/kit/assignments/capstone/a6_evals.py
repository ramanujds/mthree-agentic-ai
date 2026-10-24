"""Capstone R4 - tracing + evaluation, implemented from first principles so you understand what Phoenix / Ragas compute.
(Optional, free, local: `pip install arize-phoenix` runs a trace UI on your laptop; Ragas needs an LLM judge, which would cost money or
need a local model - so here you build deterministic, reference-based equivalents and map them to the Ragas metrics in your report.)

EXACT definitions (the autograder tests these numbers):
 context_precision(retrieved, gold) : retrieved = ordered list of doc ids, gold = list/set of relevant ids.
        average precision: mean over every relevant retrieved position i (1-based) of precision@i. No relevant retrieved -> 0.0.
        e.g. ["a","x","b"] vs {"a","b"} -> (1/1 + 2/3)/2 = 0.8333. (undefined for empty gold: skip such samples in run_eval)
 context_recall(retrieved, gold)    : |set(retrieved) & set(gold)| / |gold|
 faithfulness(answer, contexts, threshold=0.6): split the answer into sentences (on . ! ? or newline). For each sentence take its content
        tokens (harness.text.tokenize); skip sentences with none. A sentence is SUPPORTED if >= threshold of its tokens occur in the union of
        the context tokens. Score = supported / counted; 0.0 if nothing counted.
 answer_relevance(question, answer) : cosine similarity of harness.text.HashingEmbedder embeddings; 0.0 if the answer is empty.
 tool_call_accuracy(expected, actual): both lists of {"name","args"}. Greedy in-order match: each expected call matches the first unused
        later actual call with the same name whose args contain all expected key/values (extra args allowed). Score = matched / max(len(expected), len(actual)); 1.0 if both empty.
 run_eval(system_fn, dataset, clock=time.perf_counter, usd_per_1k_tokens=0.002) -> dict
        system_fn(question) -> {"answer","contexts":[str],"retrieved_ids":[str],"tool_calls":[...],"tokens_in":int,"tokens_out":int}
        dataset item: {"id","question","gold_docs":[...], optional "expected_tool_calls":[...]}
        returns {"n", "metrics": {"context_precision","context_recall","faithfulness","answer_relevance"[, "tool_call_accuracy"]} (means over samples where defined),
                 "latency_ms": {"p50","p95"} (nearest-rank percentile of per-call latency measured with `clock`),
                 "tokens": {"in","out"}, "sim_cost_usd": (in+out)/1000*usd_per_1k_tokens  <- SIMULATED, no real spend, "per_sample": [...]}
 Tracer(clock=time.perf_counter) : `with tracer.span("name", **attrs) as s:` ; nested spans get parent_id; s.set(key, value) adds attrs;
        a span that exits via exception is still closed and gets attrs["error"]=ExceptionTypeName (re-raise the exception).
        tracer.spans -> list of {"trace_id","span_id","parent_id","name","start_ms","end_ms","attrs"} (ms relative to tracer creation); tracer.to_jsonl(path)
 analyze_trace(path_or_spans) -> {"total_ms": duration of the root span, "slowest_span": name of the non-root span with the longest duration,
        "slowest_ms", "duplicate_calls": [{"name","count"}] for non-root spans sharing the same name AND attrs["input"] (count>1), most repeated first,
        "total_tokens": sum of attrs tokens_in+tokens_out over all spans, "span_count"}

Also deliver (see templates/): eval_gate.py (CLI), .github/workflows/eval.yml, eval_dataset.jsonl (20-30 items), reports/eval_baseline.json and reports/eval_after.json
(two run_eval() outputs on the SAME dataset), and a short metrics write-up (metrics_report_template.md).
"""
from __future__ import annotations
import time


def context_precision(retrieved, gold): raise NotImplementedError("capstone R4")
def context_recall(retrieved, gold): raise NotImplementedError("capstone R4")
def faithfulness(answer, contexts, threshold=0.6): raise NotImplementedError("capstone R4")
def answer_relevance(question, answer): raise NotImplementedError("capstone R4")
def tool_call_accuracy(expected, actual): raise NotImplementedError("capstone R4")
def run_eval(system_fn, dataset, clock=time.perf_counter, usd_per_1k_tokens=0.002): raise NotImplementedError("capstone R4")
def analyze_trace(path_or_spans): raise NotImplementedError("capstone R4")


class Tracer:
    def __init__(self, clock=time.perf_counter):
        raise NotImplementedError("capstone R4")

    def span(self, name, **attrs):
        raise NotImplementedError("capstone R4")

    def to_jsonl(self, path):
        raise NotImplementedError("capstone R4")
