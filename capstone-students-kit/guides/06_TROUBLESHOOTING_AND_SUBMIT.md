# 06. Troubleshooting and Submitting

## Stuck? Do this first

1. Run the checker with `-v` (kit folder): `python -m autograde.run --capstone --root . -v`. Read the reason on the failing line; it names the case that failed.
2. Re-read that file's docstring. It states the exact contract, error codes and examples.
3. Run the function by itself with `python -c "..."` before running the whole app.
4. Still stuck after 30 minutes? Ask your trainer. Send the exact command, the full error **text** (not a screenshot) and what you tried.

## Common problems

| What you see | Likely cause and fix |
|---|---|
| `ModuleNotFoundError: harness` or `a7_guard` | Wrong folder. Run `python app.py --demo` from the **capstone folder**; run the checker and pytest from the **kit folder**. Do not delete the `sys.path` block at the top of `app.py`. |
| `ModuleNotFoundError: pydantic` | The venv is not active or `pip install -r requirements.txt` was not run. |
| Checker says `not implemented yet` | That stub still raises `NotImplementedError`. Expected at the start. |
| `app.py --demo` prints "implement the --demo scenario" | You have not written the demo yet (the starting state). |
| Score is lower for the trainer than for you | The trainer uses hidden questions and attacks. Code that only works on the public examples loses points. Generalise instead of memorising. |
| `ZERO-COST SCAN: FAIL` | The message gives `file:line`. Remove the paid-SDK import, key or paid endpoint. If it is just a word in a comment, reword it. Also delete any `.env`. |
| `EVIDENCE GATE: FAIL` | Look at the `[INFO missing] EVIDENCE` lines; each says what is missing (word count, diagram, sections, both reports on the same dataset). |
| `UnicodeDecodeError` / odd characters (Windows) | `PYTHONUTF8=1`, and open files with `encoding="utf-8"`. |
| pytest says "no tests ran" | Put `test_*.py` files in `assignments/capstone/tests/` and run pytest from the kit folder. |
| Checker hangs or gets killed | A check has a time limit. Look for a loop with no exit, a real `time.sleep` in your retry code (use the injected `sleep`), or `input()`. |
| Demo works but the outage run does not print "degraded" | Print the word when a request falls back, e.g. `status: degraded - handed to a human`. |
| Escalation creates two tickets | `escalate_ticket` is not idempotent: normalise the reason and look up an existing (account, reason, priority) first. |
| Poisoned question leaks `SK-INTERNAL` | An injected sentence reached the `RuleLLM`. Sanitise **every** retrieved chunk before it goes into the tool message, and make `detect_injection` catch the "ignore all previous instructions" family. |
| Outage run crashes with `ConnectionError` | A `db.get` call is outside your try/`call_with_resilience`. Check `lookup_account_status` and anywhere else you touch `deps.db`. |
| App stays degraded after the fault clears | You cached the failure or left the circuit breaker open. After `reset_after_s` it must go half-open and let one call through (use an injected clock in tests). |
| Audit `verify()` fails on a fresh log | Hash computed over a different JSON than you verify (include/exclude `hash` consistently, same `sort_keys` and `separators`). |
| PII in the audit log | You redacted `args` at the top level only. Redact nested dicts and lists too. |
| Not sure a change broke something | Run the checker before and after and compare line by line. Keep backups or use git (`git init` in the capstone folder is fine). |

## Before you submit (checklist)

- [ ] `python -m autograde.run --capstone --root . -v` runs end to end. **EVIDENCE GATE: PASS** and **ZERO-COST SCAN: PASS**.
- [ ] From the capstone folder, `python app.py --demo` exits 0, normally **and** with `GAMEDAY_FAULT=tool_outage` (which prints "degraded").
- [ ] `python -m pytest assignments/capstone/tests` passes (kit folder).
- [ ] Every document exists and quotes numbers from **your** results; no template guidance text left.
- [ ] `reports/eval_baseline.json` and `reports/eval_after.json` use the **same** dataset.
- [ ] `audit/audit.jsonl` verifies; `traces/*.jsonl` has 5+ spans.
- [ ] No `.env`, no keys, no `__pycache__`, no `.venv` in the folder you zip.
- [ ] You can explain every function. Any AI assistant you used is named in `docs/decision_log.md`.
- [ ] Your defence slot is booked.

## Package it

From the **kit folder**:

```bash
python -m autograde.run --capstone --root . > autograde_output.txt

# clean up caches
find assignments/capstone -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -rf assignments/capstone/.pytest_cache

zip -r submission.zip assignments/capstone autograde_output.txt -x "*/__pycache__/*"
unzip -l submission.zip | head -30      # look inside: app.py present, no .venv, no .env
```

Windows: select `assignments\capstone` and `autograde_output.txt` in Explorer, then Send to > Compressed folder. PowerShell users saving the checker output: `python -m autograde.run --capstone --root . | Out-File -Encoding utf8 autograde_output.txt`.

## How you are marked (100 + up to 5 bonus)

| Part | Points |
|---|---|
| Automated checks (re-run with hidden data) | 40 |
| Trainer rubric: architecture 11, evaluation 9, reliability and security 9, business fit 8, documentation 4, engineering quality 4 | 45 |
| Defence, 30 min: viva 5, live code change 4, game day 6 | 15 |
| Stretch bonus | up to +5 |

**To pass:** total >= 60, automated >= 16/40, defence >= 6/15, evidence gate passing and zero-cost scan clean (otherwise the total is capped at 50). Late submissions lose 10 points per working day (up to 3 days).

## Defence tips

- Be ready to explain every function you wrote, and any AI assistant you used.
- The **live change** asks you to modify your code on the spot (the trainer chooses the change). Keep your code small and readable and know where each rule lives.
- The **game day**: the trainer turns on a fault. Have your probe command ready and be able to name the cause from its output.

## 5-day plan (from the participant guide)

| Day | Focus |
|---|---|
| 1 | Read the brief, data and cases. Pick a case. Run the checker. Sketch the design. |
| 2 | `a4_tools`, `a2_rag`. Start the eval dataset. |
| 3 | `a4_agent`, `a7_guard`, `a7_resilience`, `a7_audit`, then wire `app.py`. Keep `--demo` green from here. |
| 4 | `a6_evals`, `eval_gate`, CI. Baseline, find a real issue in a trace, fix it, produce the after report. |
| 5 | Documents, recorded demo, game-day rehearsal, final checker run, package. |
