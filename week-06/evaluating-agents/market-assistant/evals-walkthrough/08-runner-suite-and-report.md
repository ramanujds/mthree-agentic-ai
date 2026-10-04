# Step 7 — Runner, Suite and Report

> [Back to index](README.md) · Previous: [Fault Injection](07-fault-injection.md) · Next: [LLM Judges](09-llm-judges.md)

## Goal

Build the three files that turn the checkers and the dataset into a command: `runner.py` (run one case once), `run_suite.py` (run many cases, save results) and `report.py` (summarize them). At the end you run the whole suite for the first time, with no judges yet.

## Why this matters

A pile of checkers is not an evaluation until something runs the agent, records what happened, and summarizes it across many cases. Four decisions in this step decide whether the results can be trusted.

**A fresh sandbox for every run.** The runner creates a new `Market` and a new agent each time. If runs shared state, case E1 buying INFY would change the cash that case E2 starts with, and a result would depend on execution order. Isolation is also what makes the before/after snapshots meaningful.

**Slow things are built once, cheap things per run.** The RAG index (`Knowledge`) takes noticeable time to build and is read-only, so the suite builds it once and shares it. The `Market` is cheap and mutable, so it is rebuilt every run.

**Every run is saved as one JSONL line, in full.** The line holds the answer, every tool call with its observation, every check with its detail, the metrics and the settings used. The report is a *summary*; when a case fails you debug from the JSONL line. Writing it as the run finishes (and flushing) also means a crash at case 40 does not lose cases 1 to 39.

**Scores stay in separate columns.** Outcome, trajectory and (later) judge pass rates are reported side by side, with `SUCCESS` as their conjunction. An average would hide which dimension regressed ([note 04](../../04-llm-as-a-judge.md) makes the same point). The report also surfaces what a pass rate cannot: failure details, error kinds, redundant calls, cost, and (with several runs per case) reliability.

This is the first of two versions of `runner.py` and `run_suite.py`. The versions here have no judge code; Step 9 adds it. Records already contain the judge fields (empty for now) so the report does not change when the judges arrive.

## 1. Running one case

Create `evals/runner.py`. `execute` does the work of a single run: build the sandbox, build the agent, apply the fault, play the turns, and package the result.

```python
"""Run one case once: fresh sandbox, optional fault, all turns, then outcome / trajectory checks."""

import time
from dataclasses import asdict

from evals.checkers import run_outcome, run_trajectory
from evals.checkers.trajectory import metrics
from evals.context import CaseRun
from evals.faults import apply_fault
from market_assistant import Market, build_agent


def execute(case: dict, rep: int, knowledge, model: str | None, temperature: float, seed: int) -> CaseRun:
    client = case.get("client", "C001")
    market = Market(market_open=case.get("market_open", True))
    kwargs = {"model": model} if model else {}
    agent = build_agent(client_id=client, market=market, knowledge=knowledge, temperature=temperature, seed=seed + rep, **kwargs)
    apply_fault(agent, case.get("fault"))

    turns = case.get("turns") or [case["input"]]
    before = market.snapshot()
    history, results = [], []
    start = time.time()
    for turn in turns:
        result = agent.run(turn, history)
        history += result.turn
        results.append(result)
    return CaseRun(case, client, turns, results, before, market.snapshot(), latency_s=time.time() - start)
```

Points worth noticing: the client, market state and turns all come from the case; `seed + rep` gives each repetition a different seed (it only matters when the temperature is above zero); and `history += result.turn` is how multi-turn cases carry the conversation forward. `before` is taken once, before the first turn, and `market.snapshot()` after the last, so the diff spans the whole case.

## 2. Evaluating the run

```python
def evaluate(case: dict, rep: int, knowledge, *, model=None, temperature=0.0, seed=42) -> dict:
    ctx = execute(case, rep, knowledge, model, temperature, seed)
    outcome = run_outcome(ctx)
    traj = run_trajectory(ctx)

    outcome_pass = all(c.passed for c in outcome)
    traj_pass = all(c.passed for c in traj)
    return {
        "case_id": case["id"],
        "category": case["category"],
        "rep": rep,
        "turns": ctx.turns,
        "answer": ctx.answer,
        "stopped": ctx.stopped,
        "steps": [asdict(s) for s in ctx.steps],
        "outcome": [asdict(c) for c in outcome],
        "trajectory": [asdict(c) for c in traj],
        "judges": [],
        "outcome_pass": outcome_pass,
        "trajectory_pass": traj_pass,
        "judge_pass": None,  # judges are added in Step 9
        "judge_errors": 0,
        "success": outcome_pass and traj_pass,
        "metrics": metrics(ctx),
        "latency_s": round(ctx.latency_s, 1),
        "agent_model": model or "default",
        "judge_model": None,
        "temperature": temperature,
        "seed": seed + rep,
    }
```

`evaluate` runs the checks and flattens everything into one dictionary that can be written as JSON. `success` is the conjunction of outcome and trajectory for now. The judge fields are present but empty so the record shape is final.

## 3. The suite CLI

Create `evals/run_suite.py`. Start with the helpers and the arguments.

```python
"""Run the eval suite.

    uv run --group evals python -m evals.run_suite                       # all cases, 1 run each, code checks only
    uv run --group evals python -m evals.run_suite --ids A1,E1           # specific cases
    uv run --group evals python -m evals.run_suite --category E,F -k 5 --temperature 0.4   # reliability (pass^k)

With temperature 0 the repeated runs are (nearly) identical; use --temperature > 0 with -k > 1 to measure reliability.
"""

import argparse
import json
import time
from pathlib import Path

import yaml

from evals.report import report
from evals.runner import evaluate
from market_assistant.rag import Knowledge

HERE = Path(__file__).parent


def load_cases(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["cases"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=HERE / "datasets" / "cases.yaml")
    p.add_argument("--ids", help="comma-separated case ids")
    p.add_argument("--category", help="comma-separated categories, e.g. E,F")
    p.add_argument("-k", type=int, default=1, help="runs per case")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", help="agent model (default llama3:8b)")
    p.add_argument("--out", type=Path, default=HERE / "results")
    args = p.parse_args()
```

Selecting by `--ids` or `--category` is how you run one case while debugging. `-k` and `--temperature` are for reliability (Step 12): with temperature 0 and a fixed seed, repeated runs are nearly identical.

Then filter the cases, build the index once, and run.

```python
    cases = load_cases(args.cases)
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if args.category:
        wanted = set(args.category.split(","))
        cases = [c for c in cases if c["category"] in wanted]
    if not cases:
        raise SystemExit("no cases selected")

    knowledge = Knowledge()  # index once; every run gets a fresh Market
    args.out.mkdir(exist_ok=True)
    path = args.out / f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"

    print(f"{len(cases)} cases x {args.k} runs -> {path}\n")
    with path.open("w") as f:
        for case in cases:
            for rep in range(args.k):
                rec = evaluate(case, rep, knowledge, model=args.model, temperature=args.temperature, seed=args.seed)
                f.write(json.dumps(rec, default=str) + "\n")
                f.flush()
                failed = [c["name"] for c in rec["outcome"] + rec["trajectory"] if not c["passed"]]
                failed += [j["name"] for j in rec["judges"] if not j["passed"]]
                print(f"{'PASS' if rec['success'] else 'FAIL'}  {case['id']:<4} run {rep + 1}/{args.k}  {rec['latency_s']:>5}s  {', '.join(failed)}")

    print()
    report(path)


if __name__ == "__main__":
    main()
```

Each result is written and flushed immediately, and one progress line is printed: PASS or FAIL, the case, how long it took, and the names of the checks that failed. The report is printed at the end.

## 4. The report

Create `evals/report.py`. It reads a results file (the latest one by default) and prints. First the table builder.

```python
"""Summarise a results file: pass rates by category, reliability (pass^k), cost, invalid calls, and every failure.

    uv run --group evals python -m evals.report [results/run-....jsonl]   # default: latest run
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
NAMES = yaml.safe_load((HERE / "datasets" / "cases.yaml").read_text())["categories"]


def _rate(flags: list[bool]) -> str:
    return f"{sum(flags) / len(flags):.0%}" if flags else "-"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def table(title: str, groups: dict[str, list[dict]]) -> None:
    print(f"{title:<26}{'runs':>5}{'outcome':>9}{'traject.':>9}{'judges':>8}{'SUCCESS':>9}{'steps':>7}{'llm':>5}{'tokens':>8}")
    for name, recs in groups.items():
        judged = [r["judge_pass"] for r in recs if r["judge_pass"] is not None]
        print(
            f"{name:<26}{len(recs):>5}{_rate([r['outcome_pass'] for r in recs]):>9}"
            f"{_rate([r['trajectory_pass'] for r in recs]):>9}{_rate(judged):>8}"
            f"{_rate([r['success'] for r in recs]):>9}"
            f"{_mean([r['metrics']['steps'] for r in recs]):>7.1f}{_mean([r['metrics']['llm_calls'] for r in recs]):>5.1f}"
            f"{_mean([r['metrics']['input_tokens'] + r['metrics']['output_tokens'] for r in recs]):>8.0f}"
        )
```

Then the report body: the header, then per-category and overall rows.

```python
def report(path: Path | None = None) -> None:
    path = Path(path) if path else max((HERE / "results").glob("run-*.jsonl"))
    recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(f"Results: {path.name}   agent={recs[0]['agent_model']}  judge={next((r['judge_model'] for r in recs if r['judge_model']), 'not run')}  temperature={recs[0]['temperature']}\n")

    groups = defaultdict(list)
    for r in recs:
        groups[f"{r['category']}: {NAMES.get(r['category'], '')}"].append(r)
    table("By category", dict(sorted(groups.items())))
    print()
    table("Overall", {"all cases": recs})
```

When a case has more than one run, the report adds reliability numbers.

```python
    # reliability: only meaningful with several runs per case
    by_case = defaultdict(list)
    for r in recs:
        by_case[r["case_id"]].append(r["success"])
    k = max(len(v) for v in by_case.values())
    if k > 1:
        print(f"\nReliability over k={k} runs per case ({len(by_case)} cases):")
        print(f"  mean success rate : {_rate([s for v in by_case.values() for s in v])}")
        print(f"  pass@{k} (any run)  : {_rate([any(v) for v in by_case.values()])}   <- can it ever do it?")
        print(f"  pass^{k} (all runs) : {_rate([all(v) for v in by_case.values()])}   <- can you rely on it?")
```

`pass@k` asks "can it ever do this?" and `pass^k` asks "can you rely on it?". For an agent that moves money, `pass^k` is the number that matters, because a tool that works seven times in ten is not dependable.

Then the path-quality and cost lines, and every failing run with its details.

```python
    # path quality
    steps = [s for r in recs for s in r["steps"]]
    kinds = Counter(s["error_kind"] for s in steps if s["error"])
    print(f"\nTool calls: {len(steps)}   errors: {sum(kinds.values())} ({_rate([s['error'] for s in steps])})   by kind: {dict(kinds) or 'none'}")
    print(f"Redundant (identical repeated) calls: {sum(r['metrics']['redundant_calls'] for r in recs)}")
    pr = [(r['metrics']['tool_precision'], r['metrics']['tool_recall']) for r in recs if 'tool_precision' in r['metrics']]
    if pr:
        print(f"Tool precision / recall (cases with expected_tools): {_mean([p for p, _ in pr]):.2f} / {_mean([r for _, r in pr]):.2f}")
    eff = [r['metrics']['step_efficiency'] for r in recs if r['metrics'].get('step_efficiency')]
    if eff:
        print(f"Step efficiency (steps / minimal steps, 1.0 = ideal): {_mean(eff):.2f}")
    jerr = sum(r["judge_errors"] for r in recs)
    if jerr:
        print(f"WARNING: {jerr} judge calls failed to produce a verdict (counted as not-passed, see 'error' in the file)")

    failures = [r for r in recs if not r["success"]]
    print(f"\nFailures: {len(failures)} of {len(recs)} runs")
    for r in failures:
        print(f"\n  {r['case_id']} (run {r['rep'] + 1})  tools: {[s['tool'] for s in r['steps']]}")
        for c in r["outcome"] + r["trajectory"]:
            if not c["passed"]:
                print(f"    x {c['name']}: {c['detail']}")
        for j in r["judges"]:
            if not j["passed"]:
                print(f"    x judge:{j['name']}: {j['error'] or j['reasoning'][:200]}")
        print(f"    answer: {r['answer'][:200]!r}")
```

Failures are printed with the tools called, each failing check and its `detail`, and the start of the answer. For most failures that is enough to see the cause without opening the JSONL.

```python
if __name__ == "__main__":
    report(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
```

## Try it

Run three cases: a lookup, a trade, and the fault-injected order.

```bash
uv run --group evals python -m evals.run_suite --ids A1,E1,I5
```

Expected output (timings vary):

```
3 cases x 1 runs -> evals/results/run-20261004-051116.jsonl

PASS  A1   run 1/1    5.3s  
PASS  E1   run 1/1   12.7s  
PASS  I5   run 1/1   11.6s  

Results: run-20261004-051116.jsonl   agent=default  judge=not run  temperature=0.0

By category                runs  outcome traject.  judges  SUCCESS  steps  llm  tokens
A: Lookups                    1     100%     100%       -     100%    1.0  2.0    1985
E: Trading actions            1     100%     100%       -     100%    3.0  4.0    4960
I: Safety and robustness      1     100%     100%       -     100%    3.0  4.0    4844

Overall                    runs  outcome traject.  judges  SUCCESS  steps  llm  tokens
all cases                     3     100%     100%       -     100%    2.3  3.3    3930

Tool calls: 7   errors: 1 (14%)   by kind: {'exec_error': 1}
Redundant (identical repeated) calls: 0
Tool precision / recall (cases with expected_tools): 1.00 / 1.00
Step efficiency (steps / minimal steps, 1.0 = ideal): 1.00

Failures: 0 of 3 runs
```

The one tool error is I5's injected timeout, which is the correct behaviour. Now look at the raw record, which is what you debug from:

```bash
python3 -c "
import json, glob
rec = [json.loads(l) for l in open(sorted(glob.glob('evals/results/run-*.jsonl'))[-1])][1]
print(rec['case_id'], rec['success'], rec['answer'])
for c in rec['outcome'] + rec['trajectory']: print(' ', c['passed'], c['name'])
"
```

Then try the whole suite with `uv run --group evals python -m evals.run_suite` (about 8 to 10 minutes). Expect failures: a small local model is not perfect, and a suite that passes everything on the first run is probably not testing much. Read the failure details at the bottom of the report; each one is a real finding about the agent. You can now delete `scratch.py` and `scratch_fault.py`.

## Checkpoint

Three files. `runner.py` and `run_suite.py` are the first versions (without judges); Step 9 replaces them. `report.py` is final.

<details>
<summary>Full <code>evals/runner.py</code></summary>

```python
"""Run one case once: fresh sandbox, optional fault, all turns, then outcome / trajectory checks."""

import time
from dataclasses import asdict

from evals.checkers import run_outcome, run_trajectory
from evals.checkers.trajectory import metrics
from evals.context import CaseRun
from evals.faults import apply_fault
from market_assistant import Market, build_agent


def execute(case: dict, rep: int, knowledge, model: str | None, temperature: float, seed: int) -> CaseRun:
    client = case.get("client", "C001")
    market = Market(market_open=case.get("market_open", True))
    kwargs = {"model": model} if model else {}
    agent = build_agent(client_id=client, market=market, knowledge=knowledge, temperature=temperature, seed=seed + rep, **kwargs)
    apply_fault(agent, case.get("fault"))

    turns = case.get("turns") or [case["input"]]
    before = market.snapshot()
    history, results = [], []
    start = time.time()
    for turn in turns:
        result = agent.run(turn, history)
        history += result.turn
        results.append(result)
    return CaseRun(case, client, turns, results, before, market.snapshot(), latency_s=time.time() - start)


def evaluate(case: dict, rep: int, knowledge, *, model=None, temperature=0.0, seed=42) -> dict:
    ctx = execute(case, rep, knowledge, model, temperature, seed)
    outcome = run_outcome(ctx)
    traj = run_trajectory(ctx)

    outcome_pass = all(c.passed for c in outcome)
    traj_pass = all(c.passed for c in traj)
    return {
        "case_id": case["id"],
        "category": case["category"],
        "rep": rep,
        "turns": ctx.turns,
        "answer": ctx.answer,
        "stopped": ctx.stopped,
        "steps": [asdict(s) for s in ctx.steps],
        "outcome": [asdict(c) for c in outcome],
        "trajectory": [asdict(c) for c in traj],
        "judges": [],
        "outcome_pass": outcome_pass,
        "trajectory_pass": traj_pass,
        "judge_pass": None,  # judges are added in Step 9
        "judge_errors": 0,
        "success": outcome_pass and traj_pass,
        "metrics": metrics(ctx),
        "latency_s": round(ctx.latency_s, 1),
        "agent_model": model or "default",
        "judge_model": None,
        "temperature": temperature,
        "seed": seed + rep,
    }
```

</details>

<details>
<summary>Full <code>evals/run_suite.py</code></summary>

```python
"""Run the eval suite.

    uv run --group evals python -m evals.run_suite                       # all cases, 1 run each, code checks only
    uv run --group evals python -m evals.run_suite --ids A1,E1           # specific cases
    uv run --group evals python -m evals.run_suite --category E,F -k 5 --temperature 0.4   # reliability (pass^k)

With temperature 0 the repeated runs are (nearly) identical; use --temperature > 0 with -k > 1 to measure reliability.
"""

import argparse
import json
import time
from pathlib import Path

import yaml

from evals.report import report
from evals.runner import evaluate
from market_assistant.rag import Knowledge

HERE = Path(__file__).parent


def load_cases(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["cases"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=HERE / "datasets" / "cases.yaml")
    p.add_argument("--ids", help="comma-separated case ids")
    p.add_argument("--category", help="comma-separated categories, e.g. E,F")
    p.add_argument("-k", type=int, default=1, help="runs per case")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", help="agent model (default llama3:8b)")
    p.add_argument("--out", type=Path, default=HERE / "results")
    args = p.parse_args()

    cases = load_cases(args.cases)
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if args.category:
        wanted = set(args.category.split(","))
        cases = [c for c in cases if c["category"] in wanted]
    if not cases:
        raise SystemExit("no cases selected")

    knowledge = Knowledge()  # index once; every run gets a fresh Market
    args.out.mkdir(exist_ok=True)
    path = args.out / f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"

    print(f"{len(cases)} cases x {args.k} runs -> {path}\n")
    with path.open("w") as f:
        for case in cases:
            for rep in range(args.k):
                rec = evaluate(case, rep, knowledge, model=args.model, temperature=args.temperature, seed=args.seed)
                f.write(json.dumps(rec, default=str) + "\n")
                f.flush()
                failed = [c["name"] for c in rec["outcome"] + rec["trajectory"] if not c["passed"]]
                failed += [j["name"] for j in rec["judges"] if not j["passed"]]
                print(f"{'PASS' if rec['success'] else 'FAIL'}  {case['id']:<4} run {rep + 1}/{args.k}  {rec['latency_s']:>5}s  {', '.join(failed)}")

    print()
    report(path)


if __name__ == "__main__":
    main()
```

</details>

<details>
<summary>Full <code>evals/report.py</code></summary>

```python
"""Summarise a results file: pass rates by category, reliability (pass^k), cost, invalid calls, and every failure.

    uv run --group evals python -m evals.report [results/run-....jsonl]   # default: latest run
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
NAMES = yaml.safe_load((HERE / "datasets" / "cases.yaml").read_text())["categories"]


def _rate(flags: list[bool]) -> str:
    return f"{sum(flags) / len(flags):.0%}" if flags else "-"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def table(title: str, groups: dict[str, list[dict]]) -> None:
    print(f"{title:<26}{'runs':>5}{'outcome':>9}{'traject.':>9}{'judges':>8}{'SUCCESS':>9}{'steps':>7}{'llm':>5}{'tokens':>8}")
    for name, recs in groups.items():
        judged = [r["judge_pass"] for r in recs if r["judge_pass"] is not None]
        print(
            f"{name:<26}{len(recs):>5}{_rate([r['outcome_pass'] for r in recs]):>9}"
            f"{_rate([r['trajectory_pass'] for r in recs]):>9}{_rate(judged):>8}"
            f"{_rate([r['success'] for r in recs]):>9}"
            f"{_mean([r['metrics']['steps'] for r in recs]):>7.1f}{_mean([r['metrics']['llm_calls'] for r in recs]):>5.1f}"
            f"{_mean([r['metrics']['input_tokens'] + r['metrics']['output_tokens'] for r in recs]):>8.0f}"
        )


def report(path: Path | None = None) -> None:
    path = Path(path) if path else max((HERE / "results").glob("run-*.jsonl"))
    recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(f"Results: {path.name}   agent={recs[0]['agent_model']}  judge={next((r['judge_model'] for r in recs if r['judge_model']), 'not run')}  temperature={recs[0]['temperature']}\n")

    groups = defaultdict(list)
    for r in recs:
        groups[f"{r['category']}: {NAMES.get(r['category'], '')}"].append(r)
    table("By category", dict(sorted(groups.items())))
    print()
    table("Overall", {"all cases": recs})

    # reliability: only meaningful with several runs per case
    by_case = defaultdict(list)
    for r in recs:
        by_case[r["case_id"]].append(r["success"])
    k = max(len(v) for v in by_case.values())
    if k > 1:
        print(f"\nReliability over k={k} runs per case ({len(by_case)} cases):")
        print(f"  mean success rate : {_rate([s for v in by_case.values() for s in v])}")
        print(f"  pass@{k} (any run)  : {_rate([any(v) for v in by_case.values()])}   <- can it ever do it?")
        print(f"  pass^{k} (all runs) : {_rate([all(v) for v in by_case.values()])}   <- can you rely on it?")

    # path quality
    steps = [s for r in recs for s in r["steps"]]
    kinds = Counter(s["error_kind"] for s in steps if s["error"])
    print(f"\nTool calls: {len(steps)}   errors: {sum(kinds.values())} ({_rate([s['error'] for s in steps])})   by kind: {dict(kinds) or 'none'}")
    print(f"Redundant (identical repeated) calls: {sum(r['metrics']['redundant_calls'] for r in recs)}")
    pr = [(r['metrics']['tool_precision'], r['metrics']['tool_recall']) for r in recs if 'tool_precision' in r['metrics']]
    if pr:
        print(f"Tool precision / recall (cases with expected_tools): {_mean([p for p, _ in pr]):.2f} / {_mean([r for _, r in pr]):.2f}")
    eff = [r['metrics']['step_efficiency'] for r in recs if r['metrics'].get('step_efficiency')]
    if eff:
        print(f"Step efficiency (steps / minimal steps, 1.0 = ideal): {_mean(eff):.2f}")
    jerr = sum(r["judge_errors"] for r in recs)
    if jerr:
        print(f"WARNING: {jerr} judge calls failed to produce a verdict (counted as not-passed, see 'error' in the file)")

    failures = [r for r in recs if not r["success"]]
    print(f"\nFailures: {len(failures)} of {len(recs)} runs")
    for r in failures:
        print(f"\n  {r['case_id']} (run {r['rep'] + 1})  tools: {[s['tool'] for s in r['steps']]}")
        for c in r["outcome"] + r["trajectory"]:
            if not c["passed"]:
                print(f"    x {c['name']}: {c['detail']}")
        for j in r["judges"]:
            if not j["passed"]:
                print(f"    x judge:{j['name']}: {j['error'] or j['reasoning'][:200]}")
        print(f"    answer: {r['answer'][:200]!r}")


if __name__ == "__main__":
    report(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
```

</details>

`report.py` matches [../evals/report.py](../evals/report.py) exactly. The other two match the reference after Step 9.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `no cases selected` | Misspelled id or category on the command line | Ids are case-sensitive (`E1`, not `e1`); categories are single letters |
| Case results depend on run order | Reusing one `Market` between cases | A new `Market()` and a new agent inside `execute`, as written |
| The suite re-indexes the knowledge base for every case and is very slow | `Knowledge()` created inside the loop | Build it once in `main` and pass it down |
| `ValueError: max() iterable argument is empty` from the report | No results file yet | Run the suite first, or pass a path to `python -m evals.report` |
| Results from a crashed run are missing | Writing the whole file at the end | Write and `flush()` each record as soon as it exists |

Next: **[LLM Judges](09-llm-judges.md)**.
