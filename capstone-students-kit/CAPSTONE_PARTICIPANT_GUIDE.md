# Capstone Guide: Meridian Support Assistant

A one-page map of the kit: what each file is, what you implement, and in what order.
The full details are in the [Capstone Brief](Agentic_AI_Capstone_Brief_V1.0.docx). This guide only tells you where to look.

**Quick links**

| I want to... | Go to |
|---|---|
| Follow the step-by-step path | [kit/START_HERE.md](kit/START_HERE.md) |
| See setup, folders and zero-cost rules | [kit/README.md](kit/README.md) |
| Read the full requirements and scoring | [Capstone Brief](Agentic_AI_Capstone_Brief_V1.0.docx) (section 3 requirements, 4 layout, 6 evaluation, 9 troubleshooting) |
| Start coding | [kit/assignments/capstone/](kit/assignments/capstone/) |
| Pick a stakeholder case | [kit/data/stakeholder_interviews/](kit/data/stakeholder_interviews/) |
| Read the policy documents | [kit/data/corpus/](kit/data/corpus/) |
| Fill in a document | [kit/assignments/capstone/templates/](kit/assignments/capstone/templates/) |
| Write tests | [kit/assignments/capstone/tests/README.md](kit/assignments/capstone/tests/README.md) |
| Run the checker | [kit/autograde/run.py](kit/autograde/run.py) (run it, don't edit it) |

## 1. What you are building

**One** offline application, the Meridian Support Assistant, for a fictional bank. For every request it must:

1. **Authorise** the caller's role. A role that may not act gets a hand-over to a human and no side effect.
2. **Retrieve** policy text and treat it as data only, so a poisoned document cannot steer the model.
3. **Answer** with the right tool, cite sources, and never return raw PII.
4. **Record** one audit entry and at least 3 trace spans.
5. **Survive faults.** If the account system is down, say it is *degraded* and hand over to a human.

You then **measure** it, **break it on purpose** (game day), **document** it and **defend** it in person.

**Done looks like:**
- `python app.py --demo` exits 0 offline, and also under `GAMEDAY_FAULT=tool_outage` (prints "degraded").
- The checker shows a high score, `EVIDENCE GATE: PASS` and `ZERO-COST SCAN: PASS`.

## 2. Ground rules

- **No paid or keyed services.** No OpenAI, Anthropic, Azure or Cohere SDKs or keys, and no cloud vector DBs. Use the harness models (`RuleLLM`, `ScriptedLLM`). The scanner fails the submission otherwise.
- **No `.env`, no secrets, no real personal data.** Use only the synthetic Meridian data.
- **Do not edit `harness/`.** The trainer runs your code against their own copy.
- **Your own work.** You may use free AI assistants, but you must name them in `docs/decision_log.md` and be able to explain every line.
- **Do not memorise the public examples.** The trainer re-runs everything with hidden questions, attacks and scenarios.

## 3. What is in the kit

| Folder / file | What it is | Your job |
|---|---|---|
| [START_HERE.md](kit/START_HERE.md) | 12-step path from unzip to submission | Follow it in order |
| [README.md](kit/README.md) | Setup, folder overview, zero-cost rules | Read once |
| [assignments/capstone/](kit/assignments/capstone/) | **All your work goes here.** Stubs, `app.py`, templates | Implement and write |
| [templates/](kit/assignments/capstone/templates/) | Templates for every document, the CI workflow, the sample eval dataset and starter tests | Copy and fill with your own content |
| [stretch/](kit/assignments/capstone/stretch/) | Optional graph, memory and multi-agent stubs (up to +5 bonus) | Only if you finish early |
| [data/corpus/](kit/data/corpus/) | 12 Meridian policy documents | Read; this is your knowledge base |
| [data/stakeholder_interviews/](kit/data/stakeholder_interviews/) | Cases A, B, C | Pick **one** for your business case |
| [eval_public.jsonl](kit/data/eval_public.jsonl) | 22 public questions for RAG and evals | Use for self-testing |
| [graph_eval_public.jsonl](kit/data/graph_eval_public.jsonl) | Multi-hop questions for the stretch graph | Only for the stretch |
| [injection_attacks.jsonl](kit/data/injection_attacks.jsonl), [benign_snippets.jsonl](kit/data/benign_snippets.jsonl) | Attack and harmless text for the injection detector | Use for self-testing |
| [pii_labelled.jsonl](kit/data/pii_labelled.jsonl) | Labelled PII samples for the redactor | Use for self-testing |
| [accounts.json](kit/data/accounts.json), [fee_schedule_2025.json](kit/data/fee_schedule_2025.json) | Fake account store (contains PII) and the current fee schedule | Read only, used by the tools |
| [seeded_trace.jsonl](kit/data/traces/seeded_trace.jsonl) | A sample trace with a planted issue | Practise `analyze_trace` on it |
| [harness/](kit/harness/) | Free offline toolbox: [llm.py](kit/harness/llm.py) (fake LLMs), [text.py](kit/harness/text.py) (embedder, BM25), [corpus.py](kit/harness/corpus.py), [backends.py](kit/harness/backends.py) (fake back office), [faults.py](kit/harness/faults.py) (game-day faults), [types.py](kit/harness/types.py) | **Read only.** Do not change |
| [autograde/](kit/autograde/) | The checker the trainer runs | Run it often. Do not edit |
| [examples/](kit/examples/) | [Pydantic-AI](kit/examples/pydantic_ai_offline.py) and [LlamaIndex](kit/examples/llamaindex_workflow_offline.py) examples | Optional reference |

## 4. What to implement

Open each file. The **docstring at the top is the contract**: exact function names, error codes and examples. Suggested build order:

| # | File | Req | Implement | Key points from the contract |
|---|---|---|---|---|
| 1 | [a4_tools.py](kit/assignments/capstone/a4_tools.py) | R2 | `lookup_account_status`, `calculate_fee`, `escalate_ticket`, `search_policy` | Raise `ToolError` with the **exact** codes (`invalid_account_id`, `account_not_found`, `unknown_fee_type`, `invalid_quantity`, `unknown_plan`, `invalid_priority`, `invalid_reason`). Mask account numbers and never return name, email or phone. Use the **2025** fee schedule. `escalate_ticket` is **idempotent**: the same request returns the existing ticket (`created_new=False`). |
| 2 | [a7_guard.py](kit/assignments/capstone/a7_guard.py) | R5 | `detect_injection`, `sanitize_context`, `redact_pii`, `authorize`, `secure_answer` | Flag at least 90% of attacks and at most 10% of benign text, and generalise to **unseen** attacks. Redact email, phone, card and ID numbers and leave everything else (`$10,000`, `ACC-1001`) untouched. Least privilege follows SEC-001. Sanitise chunks **before** they reach the model. |
| 3 | [a7_audit.py](kit/assignments/capstone/a7_audit.py) | R7 | `AuditLog` with `append`, `entries`, `verify` | Append-only JSONL, hash-chained with SHA-256. Redact PII in `args` before writing. `verify()` must find the first tampered or deleted entry. |
| 4 | [a7_resilience.py](kit/assignments/capstone/a7_resilience.py) | R6 | `CircuitBreaker`, `call_with_resilience` | Retry with exponential backoff, a timeout budget, a breaker (closed, open, half-open) and a fallback. It **never raises**, and a fallback still reports the error (degradation stays visible). Sleep and clock are injected, so tests never really sleep. |
| 5 | [a2_rag.py](kit/assignments/capstone/a2_rag.py) | R1 | `build_index`, `retrieve`, `answer` | Chunking (fixed, section or semantic) and hybrid BM25+dense retrieval. Hide **superseded** documents by default. **Abstain** when the corpus has no answer. Cite sources. |
| 6 | [a4_agent.py](kit/assignments/capstone/a4_agent.py) | R3 | `handle(request, deps) -> AgentResult` | Choose the intent (`account_status`, `fee_quote`, `escalation`, `policy_question`, `transfer`, `unknown`). Policy questions go through `search_policy`. Frozen accounts and escalations set `needs_human=True`. Tool failure gives `confidence < 0.5`. It never raises and never leaks PII. |
| 7 | [a6_evals.py](kit/assignments/capstone/a6_evals.py) | R4 | 5 metrics, `run_eval`, `Tracer`, `analyze_trace` | The formulas are **exact**, so follow the docstring literally. `Tracer` spans nest and record errors. |
| 8 | [eval_gate.py](kit/assignments/capstone/eval_gate.py) | R4 | CLI quality gate | Exit **0** if all thresholds pass, **1** if any fails, **2** on usage or file errors. |
| 9 | [app.py](kit/assignments/capstone/app.py) | R8 | `build_app()`, `CapstoneApp.handle()`, and a `--demo` | Wire everything together. Get one request working end to end first, then add layers. **Keep the path block at the top of the file.** |

**Also create** (not stubs): `eval_dataset.jsonl` (20-30 of your own items, see [eval_dataset_sample.jsonl](kit/assignments/capstone/templates/eval_dataset_sample.jsonl)), `tests/` (money, PII, approvals, injection, see [starter_tests_template.py](kit/assignments/capstone/templates/starter_tests_template.py)), `.github/workflows/eval.yml` (see [ci_eval_workflow_template.yml](kit/assignments/capstone/templates/ci_eval_workflow_template.yml)), and a **probe command** that prints p95 latency, tokens per request, whether the right doc ranks first, the number of degraded answers and the slowest span.

## 5. Documents to write

Copy each template into its place, delete the guidance text, and use **your own numbers**.

| Template | Becomes |
|---|---|
| [README_template.md](kit/assignments/capstone/templates/README_template.md) | `README.md` (at least 200 words) |
| [architecture_template.md](kit/assignments/capstone/templates/architecture_template.md) | `docs/architecture.md` (with a diagram and 2+ rejected alternatives) |
| [business_case_template.md](kit/assignments/capstone/templates/business_case_template.md) | `docs/business_case.md` (Case A, B or C) |
| [runbook_template.md](kit/assignments/capstone/templates/runbook_template.md) | `docs/runbook.md` (every step must really work) |
| [threat_model_template.md](kit/assignments/capstone/templates/threat_model_template.md) | `docs/threat_model.md` (6+ threats, each with a control and a residual risk) |
| [governance_summary_template.md](kit/assignments/capstone/templates/governance_summary_template.md) | `docs/governance_summary.md` (be honest about gaps) |
| [decision_log_template.md](kit/assignments/capstone/templates/decision_log_template.md) | `docs/decision_log.md` (include any AI-assistant disclosure) |
| [gameday_report_template.md](kit/assignments/capstone/templates/gameday_report_template.md) | `gameday/gameday_report.md` |
| [demo_template.md](kit/assignments/capstone/templates/demo_template.md) | `demo/demo.md` (recorded demo of 7 minutes or less, plus script) |
| [metrics_report_template.md](kit/assignments/capstone/templates/metrics_report_template.md) | `docs/metrics_report.md` (suggested; not in the brief's layout): metric map, baseline vs after, trace findings, what each metric does not tell you |
| [framework_choice_template.md](kit/assignments/capstone/templates/framework_choice_template.md) | Fold into `docs/architecture.md` or `docs/decision_log.md` (the brief requires a framework choice or a reason for none) |
| [agent_design_brief_template.md](kit/assignments/capstone/templates/agent_design_brief_template.md) | `docs/agent_design_brief.md` (suggested): problem, contradictions found in the interview; supports R9 with the business case |
| [governance_checklist_template.md](kit/assignments/capstone/templates/governance_checklist_template.md) | Fill in as the evidence table behind `docs/governance_summary.md` |
| Your `run_eval()` output | `reports/eval_baseline.json` and `reports/eval_after.json` (same dataset) |
| Exported spans / audit log | `traces/*.jsonl`, `audit/audit.jsonl` |

## 6. Traps in the data (read the corpus!)

- **FEES-000** ([2023 fees](kit/data/corpus/fees-000-fee-schedule-2023.md)) is **superseded**. Use **FEES-001** ([2025 fees](kit/data/corpus/fees-001-fee-schedule-2025.md)): wires are $15 domestic and $40 international.
- **FAQ-001** ([customer FAQ](kit/data/corpus/faq-001-customer-faq.md)) is **poisoned** and contains injected instructions. Your pipeline must still answer the real question.
- **Approval limits** depend on amount and role: see [risk-001](kit/data/corpus/risk-001-approval-matrix.md) and [pay-001](kit/data/corpus/pay-001-wire-transfers.md). Dual control applies to wires of $10,000 and above, and AI actions above $1,000 or to a new beneficiary need human approval.
- **Roles and permissions** (least privilege for `authorize`) are in [sec-001](kit/data/corpus/sec-001-ai-usage-policy.md); who is who is in [org-001](kit/data/corpus/org-001-roles-and-branches.md).
- The account store ([accounts.json](kit/data/accounts.json)) contains **PII**. It must never appear in answers, audit entries, traces or tickets.
- The stakeholder interviews ([Case A](kit/data/stakeholder_interviews/case_A_customer_email_triage.md), [Case B](kit/data/stakeholder_interviews/case_B_card_dispute_intake.md), [Case C](kit/data/stakeholder_interviews/case_C_wire_exception_handling.md)) **contradict the policies** in places. Spot the contradictions. Related policies: [kyc-001](kit/data/corpus/kyc-001-customer-due-diligence.md), [dispute-001](kit/data/corpus/dispute-001-card-disputes.md), [support-001](kit/data/corpus/support-001-escalation.md), [acct-001](kit/data/corpus/acct-001-savings-accounts.md), [acct-002](kit/data/corpus/acct-002-current-accounts.md).

## 7. Commands

Run from the **kit folder** (the one that contains `assignments`, `autograde`, `data`, `harness`):

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m autograde.run --capstone --root . -v         # score /40, evidence gate, zero-cost scan (starts at 0)
python -m pytest assignments/capstone/tests            # your own tests
```

Run from `assignments/capstone`:

```bash
python app.py --demo                                   # must exit 0
GAMEDAY_FAULT=tool_outage python app.py --demo         # must exit 0 and print "degraded"
```

Faults for practice: `tool_outage`, `bad_retrieval`, `cost_spike`, `slow_tool`.
Re-run the checker after **every** file and read the reason on each failing line.

## 8. Suggested 5-day plan

| Day | Focus | You should have |
|---|---|---|
| 1 | Read the brief, data and cases. Pick a case. Run the checker. Sketch the design. | Chosen case, design sketch |
| 2 | `a4_tools`, `a2_rag`. Start the eval dataset. | Tools and RAG passing |
| 3 | `a4_agent`, `a7_guard`, `a7_resilience`, `a7_audit`, then wire `app.py`. | INT.1-INT.4 passing, demo green |
| 4 | `a6_evals`, `eval_gate`, CI. Baseline, find a real issue in a trace, fix it, produce the after report. | Reports, traces, INT.5-INT.7 |
| 5 | Documents, recorded demo, game-day rehearsal, final checker run, package. | Submission zip |

Keep `python app.py --demo` green from Day 3. Do not leave it to the last day.

## 9. How you are marked (100 points, plus up to 5 bonus)

| Part | Points | Notes |
|---|---|---|
| Automated checks | 40 | Re-run by the trainer with hidden data |
| Trainer rubric | 45 | Architecture 11, Evaluation 9, Reliability and security 9, Business fit 8, Documentation 4, Engineering quality 4 |
| Defence (30 min) | 15 | Viva 5, live code change 4, game day 6 |
| Stretch bonus | up to +5 | Graph and memory, multi-agent approvals |

**To pass you need all of:**
- Total of 60 or more.
- Automated score of at least 16/40.
- Defence score of at least 6/15.
- Evidence gate passing, otherwise the total is capped at 50.
- Zero-cost scan clean, otherwise the total is capped at 50.

Late submissions lose 10 points per working day (up to 3 days).

## 10. Before you submit

- [ ] Checker runs end to end. Evidence gate and zero-cost scan both PASS.
- [ ] `python app.py --demo` exits 0, normally and with `GAMEDAY_FAULT=tool_outage`.
- [ ] Every document exists and quotes numbers from **your** results.
- [ ] Baseline and after reports use the **same** dataset.
- [ ] No `.env`, keys, `__pycache__` or `.venv`.
- [ ] You can explain every function, and any AI assistant is named in `docs/decision_log.md`.
- [ ] Output saved: `python -m autograde.run --capstone --root . > autograde_output.txt`
- [ ] Zip: `zip -r submission.zip assignments/capstone autograde_output.txt -x "*/__pycache__/*"`
- [ ] Defence slot booked.

## Stuck?

Run the checker with `-v`, read the failing reason, then read that file's docstring. Still stuck after 30 minutes? Ask your trainer and send the exact command, the full error text (not a screenshot) and what you tried.
