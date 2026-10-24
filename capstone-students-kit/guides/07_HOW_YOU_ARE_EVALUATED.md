# 07. How You Are Evaluated and What to Hand In

A plain-language summary of how your capstone is marked and what you must produce. The [Capstone Brief](../Agentic_AI_Capstone_Brief_V1.0.docx) has the full requirements. This page is the short version.

## 1. The big picture

You are scored out of 100, plus up to 5 bonus points.

| Part | Points | Who scores it | When |
|---|---|---|---|
| Automated checks | 40 | The checker, re-run by your trainer with hidden data | After you submit |
| Trainer rubric | 45 | Your trainer reads your code, documents and reports | After you submit |
| Defence day | 15 | Your trainer, in person | About 30 minutes, your trainer confirms |
| Stretch bonus | up to +5 | The checker (optional) | After you submit |

**To pass you need all of these:**

- Total of 60 or more.
- Automated score of at least 16 out of 40.
- Defence score of at least 6 out of 15. This confirms the work is yours.
- Evidence gate passes. If not, your total is capped at 50.
- Zero-cost scan is clean. If not, your total is capped at 50.

**Late and resubmission:** minus 10 points per working day late, up to 3 days. One resubmission is allowed, capped at 75, with a new defence.

**Grade bands:** Distinction 85+, Merit 75+, Pass 60+, Needs improvement 45+, below 45 Not yet competent.

## 2. What you must hand in

Zip `assignments/capstone` together with `autograde_output.txt`. Do not include `__pycache__`, `.venv` or any `.env` file.

| Output | Where | What it must contain | Checked by |
|---|---|---|---|
| Working app | `app.py` | `build_app()`, `handle()`, and `python app.py --demo` that exits 0 | Checker |
| Module code | `a2_rag.py`, `a4_tools.py`, `a4_agent.py`, `a6_evals.py`, `eval_gate.py`, `a7_guard.py`, `a7_resilience.py`, `a7_audit.py` | Each stub's docstring is the contract | Checker |
| Tests | `tests/` | Tests for money, PII, approvals and injection | Trainer |
| Eval dataset | `eval_dataset.jsonl` | 20-30 items of your own | Trainer |
| Eval reports | `reports/eval_baseline.json`, `reports/eval_after.json` | Two `run_eval()` outputs on the **same** dataset, with a real improvement you can explain | Checker (format) and trainer (meaning) |
| Trace | `traces/*.jsonl` | At least 5 spans with `name`, `start_ms`, `end_ms` | Checker |
| Audit log | `audit/audit.jsonl` | At least 3 entries and `verify()` passes | Checker |
| CI workflow | `.github/workflows/eval.yml` | Runs `eval_gate.py` | Trainer |
| README | `README.md` | At least 200 words: what it is, how to run, test and evaluate | Checker (exists) and trainer |
| Architecture | `docs/architecture.md` | At least 200 words, a diagram, the request path, 2+ rejected alternatives | Checker and trainer |
| Business case | `docs/business_case.md` | Your chosen case (A, B or C), what stays human, metrics with baselines, ROI range, pilot | Checker and trainer |
| Runbook | `docs/runbook.md` | At least 300 words with health check, troubleshooting, escalation, rollback, known issues. Every step must really work | Checker and trainer |
| Governance summary | `docs/governance_summary.md` | What is satisfied (with evidence), gaps, how to close them | Checker and trainer |
| Threat model | `docs/threat_model.md` | At least 6 threats, each with a control and a residual risk | Trainer only |
| Decision log | `docs/decision_log.md` | Key decisions, and any AI assistant you used | Trainer only |
| Game-day report | `gameday/gameday_report.md` | What you saw, how you detected it, root cause, mitigation, time to detect and mitigate | Checker (exists) and trainer |
| Demo | `demo/demo.md` | Link to a recorded demo of 7 minutes or less, plus your script | Checker (exists) and trainer |
| Probe command | Your choice, e.g. `ops_check.py` | Prints p95 latency, tokens per request, whether the right document ranks first, degraded answer count, slowest span | Trainer, at game day |

Use the templates in `assignments/capstone/templates/`. Replace the guidance text, and quote numbers from **your own** runs.

## 3. Part 1: automated checks (40 points)

You can run all of these yourself on the public data:

```bash
python -m autograde.run --capstone --root . -v
```

| Check | Points | What it tests |
|---|---|---|
| RAG | 6 | Right documents retrieved, no superseded fee schedule, abstains when the corpus has no answer, cites sources |
| Tools and agent | 7 | Exact error codes, 2025 fees and allowances, masked account numbers, one ticket even if asked twice, six scenario requests |
| Evaluation and tracing | 6 | Metrics follow the docstring formulas exactly, `run_eval`, `Tracer`, `analyze_trace`, gate exit codes 0, 1, 2 |
| Safety, resilience, audit | 7 | Retry and backoff, timeout budget, circuit breaker, injection detection, PII redaction, least privilege, tamper-evident audit |
| INT.1 | 2 | Policy answers cite real documents, fee answers use the fee tool and quote the 2025 amount |
| INT.2 | 2 | Active, frozen, closed and unknown accounts, answers come from real lookups, no PII |
| INT.3 | 2 | A poisoned document cannot hijack the app and the real question still gets answered |
| INT.4 | 2 | An analyst cannot escalate, a support agent creates exactly one ticket |
| INT.5 | 2 | One verifiable audit entry per request with no raw PII, at least 3 trace spans |
| INT.6 | 2 | With the account system down you get a degraded answer and a hand-over, then it recovers |
| INT.7 | 2 | `python app.py --demo` exits 0, also with `GAMEDAY_FAULT=tool_outage` (prints "degraded") |

**Your trainer re-runs these with hidden questions, attacks, PII samples and different versions of every integration scenario.** Code that only works on the public examples loses points. Write general code, not lists of the public examples.

**Zero-cost scan.** It fails if you import a hosted-model SDK (such as OpenAI, Anthropic or Cohere), hard-code a key, call a paid endpoint, or leave a `.env` with content. Everything must run offline with the harness models.

## 4. Part 2: evidence gate (29 points, needs 23)

The checker confirms your documents and artefacts exist, are well-formed and are not filler text. It does **not** judge quality. Your trainer does that in the rubric. Look for `[INFO missing] EVIDENCE` lines in the checker output: each one tells you what is lacking.

## 5. Part 3: trainer rubric (45 points)

Your trainer reads your code, documents, reports, traces and audit log. They score what your system actually does and what your documents prove, not how polished the writing is.

| Category | Points | What earns top marks |
|---|---|---|
| Architecture and integration | 11 | Simplest design that works. Every component has a reason. The request path (guard, authorise, retrieve, tool, resilience, audit, trace) is clear and the diagram matches your code. Trade-offs and two rejected alternatives are written down |
| Evaluation and observability | 9 | Your own 20-30 item dataset. Baseline and after on the same data. One real problem found in a trace, fixed, and shown to improve. Gate wired into CI. You can say what each metric does **not** tell you |
| Reliability, security, governance | 9 | Concrete threats, each with a control and a residual risk. Honest gaps. Outages are shown to the user and handed to a human. Game-day report has real times and the correct root cause |
| Business fit | 8 | Starts from the stakeholder's real process. Separates what the assistant does from what a human must keep (money movement, exceptions, sign-off). Metrics have baselines. ROI is a range. Weakest assumption named, with a pilot to test it |
| Documentation and runbook | 4 | A new engineer can run, test and operate the system from your documents alone. Runbook steps work |
| Engineering quality and reasoning | 4 | Readable code, sensible tests on risky paths, decisions justified, any AI assistant disclosed and understood |

What your trainer will look at:

- Whether `app.py` actually routes every request through your guard, authorisation, retrieval, resilience, audit and tracing, and matches your architecture diagram.
- Whether your two eval reports come from your real runs on the same dataset, and whether the improvement can be explained from a trace.
- Whether your tests cover money, PII, approvals and injection, or only the happy path.
- Whether your business case notices where the stakeholder contradicts the policy documents.

Honesty scores well. A governance summary that lists three real gaps beats one that claims everything is satisfied. A negative or mixed result that you explain well is not marked down. Round, invented or copied figures will be questioned.

## 6. Part 4: defence day (15 points)

About 30 minutes with your trainer, on your own laptop with your own code.

| Part | Points | What happens | How to prepare |
|---|---|---|---|
| Demo | (part of the session) | You run your app and narrate one request from start to finish | Rehearse `python app.py --demo` and be able to point to each stage in the trace |
| Viva | 5 | Five questions: retrieval, safety, evaluation or observability, business fit, one free choice. 1 point is a clear, correct answer using evidence from your own system | Know why you chose your chunking and k, where each safety control sits, what your numbers mean, and what must stay human |
| Live change | 4 | The trainer sets one small change to your code, about 10 minutes. 4 = done alone, tested and explained. 3 = done alone. 2 = with hints. 1 = attempted | Keep code small and readable and know where each rule lives (roles, thresholds, redaction patterns, retry settings, spans) |
| Game day | 6 | The trainer starts your app with a hidden fault. Detection 2, diagnosis 2, mitigation 1, communication and report 1 | Rehearse all four faults against yourself and keep your probe command ready |

The four possible faults are `tool_outage`, `bad_retrieval`, `cost_spike` and `slow_tool`. See the table in [02_RUN_AND_TEST.md](02_RUN_AND_TEST.md).

**Tip for `bad_retrieval`:** the fault is applied inside the harness's own retriever. If you build retrieval on your own `a2_rag.py`, pass your results through `faults.degrade_hits(hits)` so the fault shows up in your app, otherwise you will not be able to practise it.

You are expected to explain every line you submit. Any AI assistant you used must be named in `docs/decision_log.md`. If your written work is strong but you cannot explain or change your own code, your trainer will treat that as an authorship concern.

## 7. Common ways to lose points

- Tuning to the 22 public questions or the 20 public attacks instead of generalising.
- Hiding an outage by returning a confident answer when the account system is down.
- Raw PII (card numbers, e-mails) in audit entries, trace attributes or tickets.
- Using the superseded 2023 fees (FEES-000) instead of 2025 (FEES-001), including in documents.
- Documents that describe a system you did not build, or numbers you did not measure.
- Baseline and after reports on different datasets.
- Leaving the demo until the last day. Keep `python app.py --demo` green from Day 3.
- Editing `harness/` or `autograde/`. Your trainer uses their own copies, so edits cannot help you.

## 8. Final self-check before you submit

Run from the **kit folder** unless it says otherwise.

```bash
python -m autograde.run --capstone --root . -v         # score high, EVIDENCE GATE: PASS, ZERO-COST SCAN: PASS
python -m pytest assignments/capstone/tests            # your tests pass
cd assignments/capstone
python app.py --demo                                   # exits 0
GAMEDAY_FAULT=tool_outage python app.py --demo         # exits 0 and prints "degraded"
```

- [ ] All documents exist, use the template headings, and quote your own numbers.
- [ ] `reports/eval_baseline.json` and `eval_after.json` were produced by your `run_eval()` on the same dataset.
- [ ] You have run each of the four faults against your app and your probe command shows a different result for each.
- [ ] No `.env`, keys, `__pycache__` or `.venv` in the zip.
- [ ] `autograde_output.txt` is saved and included.
- [ ] Any AI assistant is named in `docs/decision_log.md`.
- [ ] You can explain every function and change it on request.
- [ ] Your defence slot is booked.

See [06_TROUBLESHOOTING_AND_SUBMIT.md](06_TROUBLESHOOTING_AND_SUBMIT.md) for packaging commands.
