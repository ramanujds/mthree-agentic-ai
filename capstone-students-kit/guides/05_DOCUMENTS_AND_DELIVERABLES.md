# 05. Documents and Deliverables

Code is only part of the score. The **evidence gate** (29 points, needs **23**) checks that your documents and artefacts exist and are real, and the trainer's rubric (45 points) reads them. If the gate fails, your total is capped at 50.

All paths below are relative to `kit/assignments/capstone/`.

## 1. What the evidence gate checks (exactly)

| Pts | Item | Path | The checker needs |
|---|---|---|---|
| 3 | README | `README.md` | 200+ words of real content (repeated filler words do not count: at least 35% must be distinct) |
| 3 | Architecture | `docs/architecture.md` | 200+ words **and** a diagram: a ```` ```mermaid ```` block in the file, or an `.svg`/`.png`/`.drawio` file in `docs/` |
| 2 | Business case | `docs/business_case.md` | 120+ words |
| 3 | Runbook | `docs/runbook.md` | 300+ words and sections mentioning: **health** check, **troubleshoot**ing, **escalat**ion, **rollback**, **known issue**s |
| 3 | Governance summary | `docs/governance_summary.md` | 150+ words |
| 4 | Evaluation reports | `reports/eval_baseline.json`, `reports/eval_after.json` | Valid JSON with `metrics`, `latency_ms`, `sim_cost_usd` (i.e. real `run_eval()` output) |
| 3 | Exported trace | `traces/*.jsonl` | One file with 5+ spans, each having `name`, `start_ms`, `end_ms` |
| 3 | Audit log | `audit/audit.jsonl` | `AuditLog(...).verify()` is OK with 3+ entries |
| 3 | Game-day report | `gameday/gameday_report.md` | 120+ words |
| 2 | Demo | `demo/demo.md` | 60+ words (link to your recorded demo of 7 minutes or less, plus the script) |
| | **Total 29** | | **Pass mark 23** |

Run the checker and look at the `[INFO missing] EVIDENCE ...` lines; each says exactly what is lacking.

## 2. Each document: purpose and what to put in it

Copy the template from `templates/`, delete the guidance text, and write **your** content with **your** numbers.

| Document | Template | Purpose | Include |
|---|---|---|---|
| `README.md` | `README_template.md` | The front door for a stranger. | What the app does, how to install and run it, folder layout, your chunking and retrieval choice **with numbers**, how to run tests/eval. |
| `docs/architecture.md` | `architecture_template.md` | How it is built and why. | A diagram (mermaid is easiest), each module's role, the request flow, **2+ rejected alternatives** with reasons, and the framework choice (use `framework_choice_template.md` here or in the decision log). |
| `docs/business_case.md` | `business_case_template.md` | Why the bank would want this. | Your chosen **Case A, B or C**, the problem, the target, value and risk, assumptions and what you would measure. Reference the contradictions you found in the interview. |
| `docs/runbook.md` | `runbook_template.md` | How an on-call person operates it. | Health check, troubleshooting table, escalation path, rollback, known issues. **Every step must really work**; the trainer may try them. |
| `docs/threat_model.md` | `threat_model_template.md` | What can go wrong security-wise. | 6+ threats (prompt injection, PII leak, privilege escalation, tampered audit, stale policy, runaway cost...), each with a control and a residual risk. |
| `docs/governance_summary.md` | `governance_summary_template.md` (+ `governance_checklist_template.md` as the evidence table) | Compliance story against SEC-001. | What is covered, with evidence (file/test), and **honest gaps**. |
| `docs/decision_log.md` | `decision_log_template.md` | Why you chose what you chose. | Key decisions with alternatives; **name every AI assistant you used** (this is required). |
| `docs/metrics_report.md` (suggested) | `metrics_report_template.md` | Turn the numbers into insight. | Metric map to Ragas-style names, baseline vs after, the trace finding, what each metric does **not** tell you. |
| `docs/agent_design_brief.md` (suggested) | `agent_design_brief_template.md` | The problem framing. | Problem, stakeholder contradictions, scope. |
| `gameday/gameday_report.md` | `gameday_report_template.md` | Evidence you tested failure. | For each fault (`tool_outage`, `bad_retrieval`, `cost_spike`, `slow_tool`): what you saw in the probe/traces, the cause, the fix or mitigation. |
| `demo/demo.md` | `demo_template.md` | The recorded demo. | Link to the recording (7 min or less) and the script of what you show. |

## 3. Reports and artefacts (produced by running your code)

| Artefact | Path | How to produce it |
|---|---|---|
| Baseline eval | `reports/eval_baseline.json` | Run `run_eval(system_fn, dataset)` on `eval_dataset.jsonl` before you improve anything; `json.dump` the result. |
| After eval | `reports/eval_after.json` | Same dataset, after a real fix. **Do not change the dataset between the two runs.** |
| Trace | `traces/app_trace.jsonl` (or any `*.jsonl`) | The app's `Tracer.to_jsonl`. A probe run produces a good multi-span trace. |
| Audit log | `audit/audit.jsonl` | Written by your app. Run `python app.py --demo` once and keep the result (then check with `verify()`). |
| Checker output | `autograde_output.txt` (in the **kit folder**) | `python -m autograde.run --capstone --root . > autograde_output.txt` |

A minimal recipe for the reports (adapt names to your code; the capstone folder):

```python
# make_report.py (example idea)
import json, sys
import app as capstone
from a6_evals import run_eval

app = capstone.build_app()
def system_fn(q):
    r = app.handle(q)
    return {"answer": r.answer, "contexts": [...], "retrieved_ids": r.sources,
            "tool_calls": [{"name": t, "args": {}} for t in r.tools_used],
            "tokens_in": ..., "tokens_out": ...}
data = [json.loads(l) for l in open("eval_dataset.jsonl", encoding="utf-8")]
json.dump(run_eval(system_fn, data), open(sys.argv[1], "w"), indent=2)
```

The `...` parts are yours to fill in. Hint: your app can expose the retrieved chunk texts and token counts for the last request so `system_fn` can report them.

## 4. Choosing the stakeholder case

Read all three in `data/stakeholder_interviews/`, then pick **one**:

| Case | Topic |
|---|---|
| A | Customer e-mail triage (2,000 e-mails a week, fraud and complaints rules) |
| B | Card dispute intake |
| C | Wire exception handling |

For each, find where the stakeholder asks for something the policies forbid or cannot guarantee (for example "fully automatic" and "99% accurate" versus mandatory human review). Those contradictions are the heart of the business case.

## 5. Order that saves time

1. Write `eval_dataset.jsonl` while building RAG (Day 2).
2. Baseline report as soon as the app runs end to end (Day 4).
3. Draft the docs from the templates **while** you build; add numbers when you have them.
4. Record the demo last, after the final checker run.

Next: [06_TROUBLESHOOTING_AND_SUBMIT.md](06_TROUBLESHOOTING_AND_SUBMIT.md).
