# Observability and evaluation report
## 1. Metric map
Table: your metric | Ragas equivalent | what an LLM judge would add | limitation of the deterministic proxy.
## 2. Evaluation dataset (eval_dataset.jsonl, 20-30 items)
How built; coverage of question types (single-hop, multi-hop, stale-trap, unanswerable, injection); how you checked label quality.
## 3. Baseline (reports/eval_baseline.json)
Numbers and what they tell you.
## 4. Diagnosis
Trace analysis of data/traces/seeded_trace.jsonl and of your own system: slowest span, duplicate calls, token/cost hotspots. Evidence (span names, ms).
## 5. Remediation and after (reports/eval_after.json)
What you changed, why that fixes the cause, before/after table, regressions.
## 6. CI gate
Thresholds you chose and why (baseline + tolerance). How the workflow would fail a bad change.
