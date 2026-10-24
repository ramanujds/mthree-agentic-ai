# 02. Run and Test

Keep this open while you work. **Where you run a command matters**, so each block says which folder.

| Folder | Short name | Contains |
|---|---|---|
| `capstone-students-kit/kit` | **kit folder** | `assignments`, `autograde`, `data`, `harness` |
| `capstone-students-kit/kit/assignments/capstone` | **capstone folder** | your `app.py` and modules |

Remember to activate the venv first (`source .venv/bin/activate`).

## 1. The checker (your score, run it after every file)

From the **kit folder**:

```bash
python -m autograde.run --capstone --root .        # summary
python -m autograde.run --capstone --root . -v     # every sub-check and why it fails
```

How to read the output:

| Line | Meaning |
|---|---|
| `[PASS]` / `[PART]` / `[FAIL]` | A scored component (RAG, Tools and agent, Evaluation, Safety, `INT.1`..`INT.7`). |
| `    - A2.3 ...` (with `-v`) | The exact sub-check inside the component that failed, with a reason. |
| `[INFO missing] EVIDENCE ...` | A document or report the evidence gate wants and cannot find or validate. |
| `AUTOMATED SCORE: x/40` | Your automated points. |
| `EVIDENCE GATE: PASS/FAIL` | Needs 23 of 29. If it fails your total is **capped at 50**. |
| `ZERO-COST SCAN: PASS/FAIL` | Fails if you import a paid SDK, hard-code a key or keep a `.env`. If it fails your total is **capped at 50**. |

Score breakdown (40 points): RAG 6, Tools and agent 7, Evaluation and tracing 6, Safety/resilience/audit 7, Integration `INT.1`-`INT.7` 14.

Save the output for submission:

```bash
python -m autograde.run --capstone --root . > autograde_output.txt
```

Never edit anything in `autograde/`. The trainer runs it with **hidden** test data, so your score may differ slightly from yours if your code only handles the public examples.

## 2. Run the app demo

From the **capstone folder**:

```bash
python app.py --demo                                  # must exit 0
echo $?                                               # 0 means success (PowerShell: $LASTEXITCODE)
GAMEDAY_FAULT=tool_outage python app.py --demo        # must exit 0 AND print "degraded" (or "fallback")
```

PowerShell version of the fault run:

```powershell
$env:GAMEDAY_FAULT="tool_outage"; python app.py --demo; Remove-Item Env:GAMEDAY_FAULT
```

Today `--demo` exits 1 with "implement the --demo scenario". That is the starting state.

## 3. Run your tests

From the **kit folder**:

```bash
python -m pytest assignments/capstone/tests            # all your tests
python -m pytest assignments/capstone/tests -q -x      # quiet, stop at first failure
python -m pytest assignments/capstone/tests -k pii     # only tests with "pii" in the name
```

pytest finds files named `test_*.py`. [conftest.py](../kit/assignments/capstone/conftest.py) already makes `import a4_tools`, `import app` and `import harness` work, so do not add path hacks to your tests. "no tests ran" simply means you have not written any yet.

## 4. Game-day faults

The harness can break things on purpose. Set the environment variable `GAMEDAY_FAULT` to one of these when you run the demo (or your probe command):

| Fault | What it does | What you should see |
|---|---|---|
| `tool_outage` | `AccountDB.get` raises `ConnectionError` | Answer says *degraded*, `needs_human=True`, no crash, `confidence < 0.6` |
| `bad_retrieval` | Retriever returns the **least** relevant hits (reversed) | Right document no longer ranks first, answers get worse |
| `cost_spike` | Token counts are multiplied by 8 | Tokens per request jump 8x |
| `slow_tool` | Each account lookup sleeps 0.25 s | p95 latency rises, slowest span is the lookup |

In code (for tests) you can use the context manager instead of the environment variable:

```python
from harness import faults
with faults.inject("tool_outage"):
    result = app.handle("What is the status of ACC-1001?")
# after the with-block the fault is gone; your app must recover
```

## 5. The evaluation gate (once you have implemented it)

From the **capstone folder**:

```bash
python eval_gate.py reports/eval_after.json --min faithfulness=0.7 --min context_recall=0.8 --max latency_p95_ms=2000 --max sim_cost_usd=0.05
echo $?     # 0 all thresholds pass, 1 a threshold failed, 2 usage or file error
```

## 6. Try pieces on their own (fast feedback)

You do not need the whole app to test one function. From the **capstone folder**:

```bash
python -c "import a4_tools as t; from harness.deps import make_deps; d=make_deps(); print(t.lookup_account_status(d.db, 'ACC-1001'))"
python -c "import a7_guard as g; print(g.redact_pii('mail asha.verma@example.com or call +44 7700 900101'))"
python -c "import a4_tools as t; print(t.calculate_fee('international_wire'))"
```

The two tiny framework examples also run offline from the **kit folder**:

```bash
python examples/pydantic_ai_offline.py
python examples/llamaindex_workflow_offline.py
```

## 7. Self-test data files

| Data file | Use it to test |
|---|---|
| `data/eval_public.jsonl` (22 questions) | RAG: does the right document come back first? |
| `data/injection_attacks.jsonl` and `benign_snippets.jsonl` | `detect_injection`: flag >= 90% of attacks, <= 10% of harmless text |
| `data/pii_labelled.jsonl` | `redact_pii`: every listed PII string must disappear |
| `data/traces/seeded_trace.jsonl` | `analyze_trace`: it has one planted slow span and repeated calls |

A short loop to measure your detector (capstone folder):

```python
import json, a7_guard
attacks = [json.loads(l) for l in open("../../data/injection_attacks.jsonl", encoding="utf-8")]
benign  = [json.loads(l) for l in open("../../data/benign_snippets.jsonl", encoding="utf-8")]
print("attacks flagged:", sum(a7_guard.detect_injection(a["text"])["flagged"] for a in attacks), "/", len(attacks))
print("benign flagged: ", sum(a7_guard.detect_injection(b["text"])["flagged"] for b in benign), "/", len(benign))
```

## Daily routine

1. Edit one file.
2. Try it with a one-line `python -c` check.
3. Run the checker and read the failing line.
4. Run `python app.py --demo` from Day 3 on, and keep it green.

Next: [03_FOLDER_AND_FILE_MAP.md](03_FOLDER_AND_FILE_MAP.md).
