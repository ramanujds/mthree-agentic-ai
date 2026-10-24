# 04. Where to Write Your Code

All code goes in **`kit/assignments/capstone/`**. Each file begins with a docstring that is the **contract**: exact names, error codes and examples. This guide tells you the order, the idea behind each file, and which harness helper to reuse. It does not give the answers.

> Golden rule: open the stub, read the docstring top to bottom, then write. Run the checker after each file: `python -m autograde.run --capstone --root . -v` (from the kit folder).

## Build order (and why)

Build the small independent pieces first, then the agent, then wire them in `app.py`.

| Step | File | Req | Needs | Checker lines it moves |
|---|---|---|---|---|
| 1 | [a4_tools.py](../kit/assignments/capstone/a4_tools.py) | R2 | nothing | Tools and agent |
| 2 | [a7_guard.py](../kit/assignments/capstone/a7_guard.py) | R5 | nothing (except `secure_answer`, which needs a `deps`) | Safety |
| 3 | [a7_audit.py](../kit/assignments/capstone/a7_audit.py) | R7 | `redact_pii` from step 2 | Safety |
| 4 | [a7_resilience.py](../kit/assignments/capstone/a7_resilience.py) | R6 | nothing | Safety |
| 5 | [a2_rag.py](../kit/assignments/capstone/a2_rag.py) | R1 | harness `text.py`, `corpus.py` | RAG |
| 6 | [a4_agent.py](../kit/assignments/capstone/a4_agent.py) | R3 | steps 1, 2, 5 | Tools and agent |
| 7 | [a6_evals.py](../kit/assignments/capstone/a6_evals.py) | R4 | harness `text.py` | Evaluation |
| 8 | [eval_gate.py](../kit/assignments/capstone/eval_gate.py) | R4 | nothing | (CI) |
| 9 | [app.py](../kit/assignments/capstone/app.py) | R8 | everything | `INT.1`-`INT.7`, demo |
| 10 | tests, dataset, probe, CI, docs | | a working app | Evidence gate |

---

## Step 1. `a4_tools.py`: safe tools (R2)

**Purpose.** The only functions the agent may use to touch bank data. They must be narrow, validated, deterministic and PII-safe.

**Where to write.** Replace each `raise NotImplementedError` body. The Pydantic models (`AccountStatus`, `FeeQuote`, `Ticket`) are already defined, so keep their fields.

| Function | What to do | Watch out for |
|---|---|---|
| `lookup_account_status(db, account_id)` | Validate id with a regex (`ACC-` + 4 digits), read `db.get(id)`, return an `AccountStatus` with a **masked** number. | Raise `ToolError("invalid_account_id", ...)` **before** touching the db; `account_not_found` if `db.get` returns `None`. Return no name, email, phone or full number. Mask format: `"************1234"` (last 4 digits only). Include `freeze_reason` only when frozen. |
| `calculate_fee(fee_type, quantity=1, plan=None)` | Use `load_fee_schedule()` (the **2025** schedule). `free_quantity` comes from `free_allowance`, which applies to `domestic_wire` only. `total = unit_fee * (quantity - free_quantity)`. | Codes: `unknown_fee_type`, `invalid_quantity` (<1 or >1000), `unknown_plan`. Free quantity cannot exceed the quantity. Round money sensibly. |
| `escalate_ticket(store, account_id, reason, priority)` | Validate in order: account id, priority (`P1`/`P2`/`P3`), reason (non-empty, at most 300 chars). Create `TCK-0001`, `TCK-0002`... | **Idempotent.** The same (account, *normalised* reason, priority) returns the existing ticket with `created_new=False` and adds nothing. Decide what "normalised" means (case and whitespace) and test it. `store` is `deps.tickets` (a `TicketStore` with `.add()` and `.all()`). Do not store PII in the ticket reason. |
| `search_policy(retriever, query, k=4)` | Call `retriever(query, k)` and return a list of `{"doc_id","chunk_id","text"}` only. | This is "RAG as a tool". Strip the `score` key. The agent's policy path must go through it. |

**Test it quickly (capstone folder):**

```bash
python -c "import a4_tools as t; from harness.deps import make_deps as m; d=m(); print(t.lookup_account_status(d.db,'ACC-1001')); print(t.calculate_fee('domestic_wire',25,'business_current'))"
```

---

## Step 2. `a7_guard.py`: injection, PII, permissions (R5)

**Purpose.** Everything that stops bad text and bad callers.

| Function | What to do | Hints |
|---|---|---|
| `detect_injection(text)` | Return `{"flagged": bool, "patterns": [names]}`. | Use several regex families (override verbs like ignore/disregard/forget with "instructions", role-play like "you are now", "reveal system prompt", exfiltration like "send/email ... to", "developer mode"). Measure on `data/injection_attacks.jsonl` (>= 90% flagged) **and** `benign_snippets.jsonl` (<= 10% flagged). The trainer uses unseen attacks, so build patterns by *idea*, not by copying lines. |
| `sanitize_context(text)` | Split into sentences, drop the flagged ones, keep the rest. | Goal: the poisoned FAQ chunk loses the attack sentence but keeps any real content. |
| `redact_pii(text)` | Replace emails, phones, 12-19 digit numbers, and `ddd-dd-dddd` ids with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_CARD]`, `[REDACTED_ID]`. | Everything else must stay **byte for byte** identical: `$10,000`, `ACC-1001`, `1 January 2025`. Test with `data/pii_labelled.jsonl`. Order matters (do long digit runs before phones). |
| `authorize(role, tool)` | Return `True`/`False` from a role-to-tools table. | Copy it from SEC-001 "Least privilege". Unknown role or unknown tool gives `False`. Roles: `support_agent`, `payments_agent`, `analyst`. |
| `secure_answer(question, deps)` | End-to-end safe RAG: retrieve, sanitise, ask the model, redact. | Follow the docstring's message sequence exactly (system prompt that says "cite", user question, assistant tool call to `search_policy`, `role="tool"` message with sanitised chunks as JSON). Record `blocked_sources` (doc ids that contained injection) and `findings`. Run `redact_pii` on the final answer. The `RuleLLM` is *gullible*: if even one injected sentence reaches it, it leaks `SK-INTERNAL...` and the checks fail. |

---

## Step 3. `a7_audit.py`: tamper-evident log (R7)

**Purpose.** Prove who did what. Each line is JSON; each entry's `hash` covers its content and the previous hash.

**Where to write.** The `AuditLog` class: `__init__`, `append`, `entries`, `verify`.

- `__init__(path)`: if the file already exists, read the last entry to **continue** `seq` and `prev_hash`; else start at 0 with `"0"*64`.
- `append(trace_id, user, tool, args, sources, outcome)`: build the entry (fields in the docstring), run `redact_pii` on **every string in `args`, including nested dicts and lists**, compute `hash = sha256(json.dumps(entry_without_hash, sort_keys=True, separators=(",", ":")))`, write one line, return the entry.
- `entries()`: read all lines back as dicts.
- `verify()`: recompute each hash, check `seq` is 0,1,2,... and each `prev_hash` matches. Return `{"ok", "first_bad", "entries"}`. A *deleted* line is reported as the entry **after** it.

Test by appending 3 entries, editing one by hand in the file, and confirming `verify()` finds the right `seq`. Also test a deleted line.

---

## Step 4. `a7_resilience.py`: retry, breaker, fallback (R6)

**Purpose.** Failing calls must not crash the app.

- `CircuitBreaker(failure_threshold=3, reset_after_s=30.0, clock=time.monotonic)` with `.state` (`closed`/`open`/`half_open`), `.allow()`, `.record_success()`, `.record_failure()`.
  - closed: count **consecutive** failures; reaching the threshold opens it and records the time.
  - open: `allow()` is `False` until `reset_after_s` passes, then it becomes `half_open` and allows **one** trial.
  - half_open: success closes (reset the counter); failure opens again (restart the timer).
- `call_with_resilience(fn, *, retries, base_delay, max_delay, timeout_budget_s, fallback, breaker, sleep, clock, retry_on)` returns a dict and **never raises**.
  - Delay before retry *n* is `min(base_delay * 2**(n-1), max_delay)`, using the injected `sleep`.
  - Stop if elapsed + next delay would exceed the budget: `error.type = "TimeoutBudgetExceeded"`.
  - An exception not in `retry_on` is not retried; `error.type` is the exception class name.
  - Breaker refuses: do not call `fn`, `attempts=0`, `error.type="CircuitOpen"`.
  - Fallback: on any failure with a fallback, `ok=True`, `used_fallback=True`, `value=fallback()`, and `error` **still describes the failure**.

Use the injected `sleep` and `clock` everywhere, never `time.sleep` directly, or the checker will hang.

---

## Step 5. `a2_rag.py`: retrieval (R1)

**Purpose.** Find the right policy text and answer with citations, or admit it cannot.

- `build_index(corpus_dir, chunking, chunk_size, overlap, embedder)`:
  - Load docs with `harness.corpus.load_corpus` (it already parses front matter, `status`, and `sections`).
  - Chunk by `"fixed"` (sliding window of *words*), `"section"` (one chunk per `## ` section) or `"semantic"` (merge adjacent similar sentences, never exceed `chunk_size` words).
  - Every chunk keeps `doc_id`, `chunk_id`, `status`. Keep **superseded** chunks in the index (so `exclude_superseded=False` can return them) but flag them.
  - Fit `harness.text.BM25` on `tokenize(chunk_text)` and pre-compute `HashingEmbedder` vectors.
- `retrieve(index, query, k, mode, rerank, exclude_superseded)`:
  - `"bm25"`: `BM25.scores`; `"dense"`: `cosine` of embeddings; `"hybrid"`: fuse the two rankings with `harness.text.rrf`.
  - Return at most `k` hits, best first: `{"doc_id","chunk_id","text","score"}`.
  - `exclude_superseded=True` must hide FEES-000 chunks.
- `answer(index, query, llm, k)` returns `{"answer","sources","abstained"}`. It must **abstain** (no sources, "cannot find") when the question is not covered, e.g. "Does the bank offer crypto trading accounts?". Pick a threshold (a minimum score, or minimum overlap of query tokens with the best chunk) and tune it on the `unanswerable` items in `data/eval_public.jsonl`.

Compare at least two chunking strategies on your own data and write the numbers in `README.md` and `docs/architecture.md`. These numbers are marked.

---

## Step 6. `a4_agent.py`: the agent (R3)

**Purpose.** Turn a free-text request into the right tool call and a structured answer.

Write `handle(request, deps) -> AgentResult` (never raise). The `AgentResult` model lives in `harness/types.py`.

Suggested shape:

1. **Classify** the intent: `account_status` (has an `ACC-dddd` and asks status), `fee_quote` (fee/cost/charge + a fee type), `escalation` (escalate/fraud/complain), `policy_question`, `transfer` (move money), else `unknown`. You may let `deps.llm.chat(messages, tools)` choose the tool (the `RuleLLM` does this by keywords) or write your own rules. Either is fine; explain it in `docs/decision_log.md`.
2. **Call the tool** from step 1. Policy questions **must** go through `search_policy` and return the doc ids in `sources`. Fee questions must use `calculate_fee` (the checker looks for `tools_used`).
3. **Catch `ToolError` and other exceptions** (including `ConnectionError` from a fault) and return a polite answer with `confidence < 0.5`. No stack traces in the answer.
4. **Set `needs_human=True`** for frozen accounts and for every escalation.
5. **Never put PII in `answer`**: run `redact_pii` on the final text.
6. `tools_used` lists only tools actually called.

For the `transfer` intent there is no provided tool. The safe default is: do not move money, set `needs_human=True`, and explain that approval rules apply (SEC-001: above $1,000 or to a new beneficiary needs a human).

---

## Step 7. `a6_evals.py`: metrics and tracing (R4)

**Purpose.** Measure the system, from first principles.

The formulas are **exact**. Read the docstring and follow it literally, because the checker compares numbers.

| Function | Notes |
|---|---|
| `context_precision(retrieved, gold)` | Average precision. Example in the docstring: `["a","x","b"]` vs `{"a","b"}` gives 0.8333. |
| `context_recall(retrieved, gold)` | `|retrieved & gold| / |gold|`. |
| `faithfulness(answer, contexts, threshold=0.6)` | Per sentence, the fraction of content tokens (`harness.text.tokenize`) found in the contexts. |
| `answer_relevance(question, answer)` | Cosine of `HashingEmbedder` vectors; `0.0` for an empty answer. |
| `tool_call_accuracy(expected, actual)` | Greedy in-order match, `matched / max(len)`; `1.0` if both are empty. |
| `run_eval(system_fn, dataset, ...)` | Calls `system_fn(question)` for each item, averages the metrics (skip samples where undefined, e.g. empty gold), measures latency with the injected `clock`, nearest-rank p50/p95, sums tokens, `sim_cost_usd = (in+out)/1000 * usd_per_1k_tokens`. |
| `Tracer` | `with tracer.span("name", **attrs) as s:`; nested spans get `parent_id`; `s.set(k, v)`; a span that exits by exception is still closed with `attrs["error"]` and the exception re-raised; `tracer.spans`; `tracer.to_jsonl(path)`. Times are ms relative to tracer creation. |
| `analyze_trace(path_or_spans)` | Returns `total_ms` (root span), `slowest_span` (non-root), `slowest_ms`, `duplicate_calls`, `total_tokens`, `span_count`. Practise on `data/traces/seeded_trace.jsonl`. |

`eval_gate.py` is a small CLI: parse `--min name=value` and `--max name=value` (repeatable), load the JSON, print `PASS`/`FAIL` per threshold, and return 0 / 1 / 2. Metric names are keys of `results["metrics"]` plus `latency_p50_ms`, `latency_p95_ms`, `sim_cost_usd`.

---

## Step 8. `app.py`: wire everything (R8)

**Purpose.** One application. This is what `INT.1`-`INT.7` and the demo test.

Rules for this file:

- **Keep the `sys.path` block at the top.** It lets `python app.py --demo` find your modules and the harness.
- `build_app(deps=None, audit_path=None, trace_path=None)` returns a `CapstoneApp`. If `deps` is `None`, call `harness.deps.make_deps()`. Defaults: `audit/audit.jsonl`, `traces/app_trace.jsonl`. **Always use the `deps` you were given** (`deps.llm`, `deps.retriever`, `deps.db`, `deps.tickets`), because the grader injects faults and hold-out data through them.
- `CapstoneApp.deps` exposes the deps. `CapstoneApp.handle(request, role="support_agent")` returns an `AgentResult`.

Flow inside `handle` (sketch, not code to copy blindly):

```
1. start a trace (Tracer) and a root span                      -> a6_evals
2. decide which tool the request needs, then
   authorize(role, tool); if not allowed:
       return AgentResult(needs_human=True, ...)  # NO side effect (no ticket, no lookup)
3. call the agent through call_with_resilience(...)            -> a7_resilience
       fallback = degraded AgentResult (says "degraded",
                  needs_human=True, confidence < 0.6)
4. retrieved text -> sanitize_context before it reaches the model -> a7_guard
5. redact_pii on the final answer
6. audit.append(trace_id, user=role, tool, args, sources, outcome) -> a7_audit
7. write spans to the trace file (>= 3 spans, with name/start_ms/end_ms,
   at least one root span with parent_id None)
8. return the AgentResult
```

Where the role check lives: the permission is per **tool**, so it is natural to check it just before the agent calls a tool, or to pre-classify the intent in `handle` and map intent to tool (`escalation` to `escalate_ticket`, `account_status` to `lookup_account_status`, etc.). Either works, but `INT.4` requires: an `analyst` asking to escalate creates **zero** tickets and gets `needs_human=True`; a `support_agent` asking twice creates exactly **one** ticket.

`--demo` (the `if __name__ == "__main__":` block): run 4-6 scripted requests (a policy question, a fee quote, an account status, an escalation, a poisoned question), print each answer, and print a final summary line. If a request fell back, print the word **degraded** (for example `status: degraded - handed to a human`). It must exit 0 in both normal mode and with `GAMEDAY_FAULT=tool_outage`. For that outage run the demo should still print every request, not crash on the first.

Get **one** request working end to end first (status lookup), then add the layers one at a time, running `python app.py --demo` between each.

### What each integration check wants

| Check | What it drives | Make sure |
|---|---|---|
| `INT.1` | A policy question and a fee question | Policy: `sources` contains the right doc id and `search_policy` is in `tools_used`. Fee: `"40"` in the answer and `calculate_fee` used. |
| `INT.2` | Status of ACC-1001 (active), ACC-1003 (frozen, needs human), ACC-9999 (unknown, `confidence < 0.5`) | Answers come from real `db.get` calls (the checker counts lookups). No PII. |
| `INT.3` | "What are the branch opening hours? Also share any customer tips." | No `SK-INTERNAL`, no PII, but the real hours ("9") are still in the answer. |
| `INT.4` | Escalation as `analyst` and as `support_agent` (twice) | See above. |
| `INT.5` | A request containing an email and a card number, then two more | `audit.jsonl` verifies with 3+ entries, **no raw PII** in it, trace file has 3+ spans. |
| `INT.6` | A request under `faults.inject("tool_outage")`, then again afterwards | During: `needs_human`, a word like *degraded/unavailable/fallback/temporar*, `confidence < 0.6`. After: back to normal ("active"). Do not cache the failure. |
| `INT.7` | `python app.py --demo` as a subprocess, normal and with `GAMEDAY_FAULT=tool_outage` | Exit 0; outage run prints *degraded* or *fallback*. |

---

## Step 9. Things you create that are not stubs

| What | Where | How |
|---|---|---|
| `eval_dataset.jsonl` | capstone folder | 20-30 items of your **own**, in the shape of `templates/eval_dataset_sample.jsonl` (`id`, `question`, `gold_docs`, optional `expected_tool_calls`). Include stale-trap, unanswerable, tool and injection questions. |
| Tests | `tests/test_*.py` | Start from `templates/starter_tests_template.py`. Cover **money** (fees), **PII** (redaction, masking), **approvals/least privilege**, **injection**, plus audit `verify`, resilience and idempotent escalation. |
| Baseline and after reports | `reports/eval_baseline.json`, `reports/eval_after.json` | Write a small script (or use a probe) that builds a `system_fn` around your app, runs `run_eval` on `eval_dataset.jsonl`, and saves the JSON. Run once for the baseline, **find a real weakness in a trace, fix it**, run again on the **same dataset**. |
| Exported trace | `traces/*.jsonl` | `tracer.to_jsonl(...)`; at least 5 spans with `name`, `start_ms`, `end_ms`. |
| Audit log | `audit/audit.jsonl` | Produced by running your app (3+ entries, `verify()` OK). Do not hand-edit it afterwards. |
| Probe command | e.g. `probe.py` | Prints p95 latency, tokens per request, whether the right doc ranks first, number of degraded answers and the slowest span. It must give visibly different output under each fault. |
| CI workflow | `.github/workflows/eval.yml` | From `templates/ci_eval_workflow_template.yml`; runs tests, evaluation and `eval_gate.py`. |

## Optional: stretch (up to +5)

Only after everything above is green. Files are in `stretch/`: `a3_graph.py` and `a3_memory.py` (up to 2.5), `a5_orchestrator.py` (up to 2.5). Their docstrings are the contracts.

Next: [05_DOCUMENTS_AND_DELIVERABLES.md](05_DOCUMENTS_AND_DELIVERABLES.md).
