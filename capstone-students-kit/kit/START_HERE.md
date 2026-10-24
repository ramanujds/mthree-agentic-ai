# START HERE - Capstone (learners)

Follow these steps in order. The Capstone Brief explains the details behind each one.

## What you need
- **A laptop**: Windows, macOS or Linux. No GPU, no cloud account, no API key, no paid software.
- **Python**: 3.11 or newer (3.13 is what the kit was tested on). Check with `python --version`.
- **A terminal and an editor**: Any. You will run short commands in the kit folder.
- **Internet**: Only once, for `pip install`. After that everything runs offline.
- **Time**: About five working days (see the timeline in section 5), then a 30-minute defence.

## Your path
| Step | Do this | You know it worked when |
|---|---|---|
| 1  Unpack | Unzip `capstone_learner_kit.zip`. Open a terminal **in the `kit` folder** (the one that contains `assignments`, `autograde`, `data`, `harness`). Every command below is run from there unless it says otherwise. | `ls` (or `dir`) shows `assignments`, `autograde`, `data`, `harness`, `requirements.txt`. |
| 2  Install | `python -m venv .venv`, then activate it (macOS/Linux: `source .venv/bin/activate`; Windows: `.venv\Scripts\activate`), then `pip install -r requirements.txt`. | `pip` finishes without an error. Your prompt starts with `(.venv)`. |
| 3  See the starting line | `python -m autograde.run --capstone --root .` then add `-v` to see every check and the reason it fails. | You see `AUTOMATED SCORE: 0.0/40` and `ZERO-COST SCAN: PASS`. Nothing is broken: the stubs simply are not implemented yet. |
| 4  Understand the case | Read the three interviews in `data/stakeholder_interviews/`, choose Case A, B or C, then skim `data/corpus/`. Note the traps: the superseded fee schedule (FEES-000), the poisoned FAQ (FAQ-001) and the amount- and role-dependent approval limits. | You can say in two sentences what your stakeholder wants and one thing they get wrong. |
| 5  Build the pieces | In `assignments/capstone/` implement the stubs. A good order: `a4_tools.py`, `a7_guard.py`, `a7_audit.py`, `a7_resilience.py`, `a2_rag.py`, `a4_agent.py`, `a6_evals.py`, `eval_gate.py`. Each stub's docstring is the contract. Re-run the checker after each file. | The matching component line changes from FAIL to PASS (use `-v` for the detail). |
| 6  Wire the app | Implement `build_app()` and `handle()` in `app.py` and a `--demo` scenario. Start with one request all the way through (authorise, retrieve or tool, answer, audit, trace), then add layers. | From `assignments/capstone`, `python app.py --demo` exits 0 and prints answers. INT.1-INT.7 start to pass. |
| 7  Test the risky paths | Write tests in `assignments/capstone/tests/` for money, PII, approvals and injection (start from `templates/starter_tests_template.py`). From the kit folder: `python -m pytest assignments/capstone/tests`. | pytest reports passed tests, including at least one for each risky path. |
| 8  Measure and improve | Write `eval_dataset.jsonl` (20-30 items). Run `run_eval()` to get `reports/eval_baseline.json`. Use your traces to find a real weakness, fix it, then produce `reports/eval_after.json` on the same dataset. Export a trace to `traces/` and an audit log to `audit/`. Add the CI workflow from `templates/`. | The two reports differ for a reason you can point at in a trace. |
| 9  Rehearse the game day | Run your app with `GAMEDAY_FAULT=tool_outage`, then `bad_retrieval`, `cost_spike` and `slow_tool` (Windows PowerShell: `$env:GAMEDAY_FAULT="tool_outage"`). Build one probe command that prints p95 latency, tokens per request, whether the right document ranks first, how many answers were degraded and the slowest span. | Your probe output looks different for each fault, and you can name the cause from it. |
| 10  Write the documents | Copy each file from `assignments/capstone/templates/` to its place in the layout in section 4 (for example `architecture_template.md` becomes `docs/architecture.md`; `README_template.md` becomes `README.md`), replace the guidance text with content from your own system and quote your own numbers. Record any AI-assistant use in `docs/decision_log.md`. | The EVIDENCE lines in the checker output show no `missing` entries. |
| 11  Final check | From the kit folder: `python -m autograde.run --capstone --root . -v`. Save the output as `autograde_output.txt` (macOS/Linux/cmd: `python -m autograde.run --capstone --root . > autograde_output.txt`; PowerShell: `python -m autograde.run --capstone --root . / Out-File -Encoding utf8 autograde_output.txt`). Run `python app.py --demo` both normally and with `GAMEDAY_FAULT=tool_outage`. | The score is as high as you can get it, `EVIDENCE GATE: PASS`, `ZERO-COST SCAN: PASS`, and both demo runs exit 0 (the outage run prints 'degraded'). |
| 12  Package and send | Delete any `__pycache__` folders and any `.env` file. Zip the `assignments/capstone` folder together with `autograde_output.txt` (macOS/Linux: `zip -r submission.zip assignments/capstone autograde_output.txt -x "*/__pycache__/*"`; Windows: select both in Explorer, Send to > Compressed folder). Send it to your trainer by the deadline and book your defence slot. | You open the zip and see `assignments/capstone/app.py` inside, and no `.venv` folder. |

## If you get stuck
1. Run the checker with `-v` and read the reason on the failing line. It names the case that failed.
2. Read the docstring of the stub: it states the exact contract, error codes and examples.
3. Run the small piece by itself in a Python session before running the whole app.
4. Still stuck after 30 minutes? Ask your trainer. Send the command you ran, the full message you saw (copy the text, not a screenshot) and what you already tried.
5. You may discuss ideas and error messages with others and use free tools, but the code and documents you submit must be your own, you must be able to explain every line, and any AI assistant you used must be named in `docs/decision_log.md`. The live change in the defence tests this.

## Common problems
| What you see | What to do |
|---|---|
| `ModuleNotFoundError: harness` (or `a7_guard`) | Run `python app.py --demo` from inside `assignments/capstone`, and the checker and pytest from the kit folder. Do not delete the small path block at the top of `app.py`. |
| `pip install` fails or is very slow | Check `python --version` (3.11+), upgrade pip with `python -m pip install --upgrade pip`, make sure the virtual environment is active, and retry on a stable connection. |
| The checker says `not implemented yet` | That stub still raises `NotImplementedError`. Implement it; this message is expected at the start. |
| The checker score is lower for the trainer than for you | The trainer re-runs the checks with hidden questions, attacks and scenarios. Code that only works for the public examples loses points. Generalise instead of memorising. |
| `ZERO-COST SCAN: FAIL` | The message gives `file:line`. Remove the paid-SDK import, the key or the paid endpoint. If it is only a harmless word in a comment, reword the comment. |
| `EVIDENCE GATE: FAIL` or `[INFO missing]` lines | Each line says what the file needs (for example a word count, a diagram, required headings or two reports from the same dataset). Fix the file and re-run. |
| Strange characters or `UnicodeDecodeError` on Windows | Set `PYTHONUTF8=1` before running (PowerShell: `$env:PYTHONUTF8="1"`) and open your own files with `encoding="utf-8"`. |
| `python -m pytest` finds nothing | Put files named `test_*.py` in `assignments/capstone/tests/` and run pytest from the kit folder. |
| The checker hangs or is killed | A check has a time limit. Look for a loop with no exit, a retry with real `time.sleep`, or code waiting for `input()`. Inject `sleep`/`clock` as the resilience contract says. |
| `app.py --demo` works but the outage run does not print 'degraded' | Print the word in the answer or the demo summary when a request falls back (for example `status: degraded - handed to a human`). |
| You are not sure a change broke something | Run the checker before and after the change and compare the scores line by line. Commit often. |
