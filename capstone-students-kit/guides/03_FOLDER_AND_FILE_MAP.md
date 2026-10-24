# 03. Folder and File Map

What every folder and file is for. Legend:

- **WRITE** = you implement or create this. 
- **READ** = use it as input or reference. 
- **DON'T TOUCH** = changing it can break grading.

## Top level (`capstone-students-kit/`)

| Item | Purpose |
|---|---|
| `Agentic_AI_Capstone_Brief_V1.0.docx` | **READ.** The official brief: requirements (section 3), folder layout (4), evaluation (6), troubleshooting (9). |
| `CAPSTONE_PARTICIPANT_GUIDE.md` | **READ.** One-page map of the whole kit. |
| `guides/` | **READ.** These guides. |
| `kit/` | The actual project. Everything below is inside it. |

## `kit/` (the "kit folder": run most commands from here)

| Item | Purpose | Action |
|---|---|---|
| `README.md` | Short setup, rules and checks. | READ |
| `START_HERE.md` | 12-step path from unzip to submission, plus common problems. | READ |
| `requirements.txt` | Python packages (all free). | Leave as is. Do not add paid SDKs. |
| `assignments/capstone/` | **All your work lives here.** | **WRITE** |
| `harness/` | Free offline toolbox (fake LLMs, retriever, fake bank systems, fault injection). | **DON'T TOUCH** (the trainer uses their own copy) |
| `autograde/` | The checker the trainer runs. | **DON'T TOUCH**, only run it |
| `data/` | Synthetic bank data: policies, accounts, test sets, interviews. | READ only |
| `examples/` | Two tiny framework demos (Pydantic-AI, LlamaIndex) that run without any API key. | READ (optional reference) |

## `kit/assignments/capstone/` (the "capstone folder": your workspace)

### Code you implement (each file starts as a stub that raises `NotImplementedError`)

| File | Requirement | One-line purpose | Main things to write |
|---|---|---|---|
| `a4_tools.py` | R2 Tools | Narrow, safe functions the agent can call. | `lookup_account_status`, `calculate_fee`, `escalate_ticket`, `search_policy` |
| `a7_guard.py` | R5 Security | Stops prompt injection, hides PII, enforces role permissions. | `detect_injection`, `sanitize_context`, `redact_pii`, `authorize`, `secure_answer` |
| `a7_audit.py` | R7 Audit | Tamper-evident, append-only log (hash chain). | `AuditLog.append / entries / verify` |
| `a7_resilience.py` | R6 Reliability | Retry, backoff, timeout budget, circuit breaker, fallback. | `CircuitBreaker`, `call_with_resilience` |
| `a2_rag.py` | R1 RAG | Chunk and index the policy docs, search them, answer with citations or abstain. | `build_index`, `retrieve`, `answer` |
| `a4_agent.py` | R3 Agent | Picks the intent, calls the right tool, returns a structured result. | `handle(request, deps) -> AgentResult` |
| `a6_evals.py` | R4 Evaluation | Metrics (5), `run_eval`, tracing, trace analysis. | 5 metric functions, `run_eval`, `Tracer`, `analyze_trace` |
| `eval_gate.py` | R4 CI gate | Command-line pass/fail on metric thresholds. | `main()` |
| `app.py` | R8 Integration | **Wires everything into ONE app** and provides `--demo`. | `build_app()`, `CapstoneApp.handle()`, demo scenario |

### Support files already provided

| File | Purpose | Action |
|---|---|---|
| `conftest.py` | Makes imports work in pytest (adds the capstone and kit folders to `sys.path`). | Leave as is |
| `tests/README.md` | Says where tests go. | **WRITE** your `test_*.py` files here |
| `templates/` | One template per document, plus a CI workflow, sample dataset and starter tests. | Copy, then fill with **your own** content |
| `stretch/` | Optional extras worth up to +5 bonus points. | Only if you finish early |

### `stretch/` (optional)

| File | Purpose |
|---|---|
| `a3_graph.py` | Knowledge graph from the corpus with networkx; `extract_triples`, `build_graph`, `graph_retrieve` (multi-hop questions, `data/graph_eval_public.jsonl`). |
| `a3_memory.py` | `ConversationMemory` that keeps pinned facts and recent turns within a token budget. |
| `a5_orchestrator.py` | Router plus specialist agents with a human-approval gate for money movement; idempotent `run`/`resume`. |

### `templates/` (copy, rename, fill in)

| Template | Becomes (inside the capstone folder) |
|---|---|
| `README_template.md` | `README.md` |
| `architecture_template.md` | `docs/architecture.md` |
| `business_case_template.md` | `docs/business_case.md` |
| `runbook_template.md` | `docs/runbook.md` |
| `threat_model_template.md` | `docs/threat_model.md` |
| `governance_summary_template.md` | `docs/governance_summary.md` |
| `governance_checklist_template.md` | Evidence table behind the governance summary |
| `decision_log_template.md` | `docs/decision_log.md` |
| `framework_choice_template.md` | Fold into `docs/architecture.md` or `docs/decision_log.md` |
| `agent_design_brief_template.md` | `docs/agent_design_brief.md` |
| `metrics_report_template.md` | `docs/metrics_report.md` |
| `gameday_report_template.md` | `gameday/gameday_report.md` |
| `demo_template.md` | `demo/demo.md` |
| `eval_dataset_sample.jsonl` | Shape for your own `eval_dataset.jsonl` (20-30 items) |
| `ci_eval_workflow_template.yml` | `.github/workflows/eval.yml` |
| `starter_tests_template.py` | `tests/test_risky_paths.py` (then extend) |

## `kit/harness/` (read-only toolbox; know what is in it)

| File | What it gives you |
|---|---|
| `deps.py` | `Deps` dataclass (`llm`, `db`, `ledger`, `tickets`, `retriever`, `user_role`) and `make_deps(role)` that builds a working set. **Your app must use these** so the trainer can inject faults and hold-out data. |
| `llm.py` | Fake models: `RuleLLM` (default; picks tools from keywords; deliberately gullible to injected instructions), `ScriptedLLM` (plays back fixed replies, ideal for unit tests), `MockExtractionLLM` (stretch graph), `LoopingLLM` / `FlakyLLM` (misbehaving models), `OllamaLLM` (optional local model). Call with `llm.chat(messages, tools)`. |
| `text.py` | `tokenize`, `count_tokens`, `HashingEmbedder` (`embed`, `embed_many`), `cosine`, `BM25` (`fit`, `scores`), `rrf` (rank fusion), `extractive_summary`. |
| `corpus.py` | `load_corpus(dir)` returns `Doc` objects with `doc_id`, `status` (current/superseded), `text`, and `sections` as (heading, body). |
| `retriever.py` | `BaselineRetriever`: a ready BM25 retriever over *current* docs. `deps.retriever(query, k)` returns `[{doc_id, chunk_id, text, score}]`. |
| `backends.py` | Fake bank systems: `AccountDB.get(id)` (raw PII!), `TicketStore`, `Ledger` (`post_transfer` has **no** idempotency of its own), `load_fee_schedule()`. |
| `faults.py` | Game-day faults: `inject(name)`, `is_active(name)`, env var `GAMEDAY_FAULT`. |
| `types.py` | `ToolError(code, message)`, `AgentResult`, `ApprovalRequest`, `ApprovalDecision`, `RunResult`. |
| `traces.py` | Generates the seeded practice trace. |

## `kit/data/` (all synthetic)

| Item | Purpose |
|---|---|
| `corpus/` | **12 policy documents** = your knowledge base. Doc ids: ACCT-001/002, DISPUTE-001, FAQ-001, FEES-000/001, KYC-001, ORG-001, PAY-001, RISK-001, SEC-001, SUPPORT-001. |
| `stakeholder_interviews/` | Cases A (email triage), B (card dispute intake), C (wire exception handling). Pick **one** for your business case. They contradict the policies in places. Find those. |
| `eval_public.jsonl` | 22 questions with gold documents (types: single, multi, stale_trap, unanswerable, injection_trap). Self-test RAG with it. |
| `graph_eval_public.jsonl` | Multi-hop questions (stretch graph only). |
| `injection_attacks.jsonl`, `benign_snippets.jsonl` | Attack and harmless text for `detect_injection`. |
| `pii_labelled.jsonl` | Text with labelled PII for `redact_pii`. |
| `accounts.json` | Fake account store, **contains PII** (names, emails, phones, account numbers). Accounts ACC-1001... Used by `AccountDB`. Never let it reach an answer, log, trace or ticket. |
| `fee_schedule_2025.json` | Current fees (domestic wire $15, international $40...). Used by `calculate_fee`. |
| `extraction_oracle.json` | Answer key for the stretch graph extractor mock. |
| `traces/seeded_trace.jsonl` | A sample trace with a planted slow span and repeated calls. Practise `analyze_trace`. |

### The traps in the data (read the corpus!)

1. **FEES-000 is superseded.** Use FEES-001. Your retriever must hide superseded docs by default.
2. **FAQ-001 is poisoned.** One section contains injected instructions. A good pipeline still answers the real question (opening hours 9 AM to 5 PM weekdays).
3. **Approvals depend on amount and role** (RISK-001, PAY-001, SEC-001).
4. **Accounts contain PII.**
5. **Interviews contradict policy.** For example, a stakeholder asking for "fully automatic, 99% accurate".

## `kit/autograde/` (do not edit; run it)

| File | Purpose |
|---|---|
| `run.py` | Entry point: `python -m autograde.run --capstone --root .` |
| `checks_cap.py` | The capstone grader: component checks, `INT.1`-`INT.7` integration checks, the evidence gate and stretch bonus. **Read it to see exactly what is tested.** |
| `checks_a2.py`, `a4`, `a6`, `a7` | Per-component checks (RAG, tools/agent, evaluation, safety). |
| `checks_a3.py`, `checks_a5.py` | Stretch checks (graph/memory, orchestrator). |
| `checks_a8.py` | The evidence gate: documents, reports, traces, audit log, demo. |
| `checks_a1.py` | Not used by the capstone. |
| `framework.py` | Helper used by the checks. |
| `zero_cost_scan.py` | The scan that looks for paid SDKs, keys and `.env` files. |

## `kit/examples/`

| File | Purpose |
|---|---|
| `pydantic_ai_offline.py` | A Pydantic-AI agent with a fake model (no key). Reference if you choose that framework. |
| `llamaindex_workflow_offline.py` | A LlamaIndex Workflow with a mock LLM. Reference if you choose that framework. |

You do **not** need either framework. A hand-written loop is allowed as long as you explain the choice in `docs/decision_log.md`.

## What the finished capstone folder should look like

```
assignments/capstone/
  app.py  a2_rag.py  a4_tools.py  a4_agent.py  a6_evals.py
  a7_guard.py  a7_audit.py  a7_resilience.py  eval_gate.py  conftest.py
  eval_dataset.jsonl          <- 20-30 of your own items
  probe.py (or similar)       <- the game-day probe command
  README.md                   <- 200+ words
  docs/       architecture.md  business_case.md  runbook.md  governance_summary.md
              threat_model.md  decision_log.md  (+ optional metrics_report.md, agent_design_brief.md)
  reports/    eval_baseline.json  eval_after.json
  traces/     *.jsonl         <- exported spans (5+)
  audit/      audit.jsonl     <- verifiable log (3+ entries)
  gameday/    gameday_report.md
  demo/       demo.md
  tests/      test_*.py
  .github/workflows/eval.yml
  stretch/                    <- optional
  templates/                  <- may stay
```

Next: [04_WHERE_TO_WRITE_CODE.md](04_WHERE_TO_WRITE_CODE.md).
