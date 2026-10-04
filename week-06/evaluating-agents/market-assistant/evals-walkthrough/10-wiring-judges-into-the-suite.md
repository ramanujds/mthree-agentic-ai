# Step 9 — Wiring Judges into the Suite

> [Back to index](README.md) · Previous: [LLM Judges](09-llm-judges.md) · Next: [Calibrating the Judges](11-calibrating-the-judges.md)

## Goal

Update `runner.py` and `run_suite.py` so that cases with a `judges:` list get those judges run on request, and the report's judge column fills in.

## Why this matters

The judges are the slowest and least reliable part of the harness: each is a model call, and the model can be wrong. So they are **opt-in** (`--judges`). A quick check while editing the agent should be able to run all the code checks in minutes and skip the judges; a full evaluation turns them on.

This step is also where the separation of concerns pays off. The checkers did not change at all, the report did not change, and the record shape was already final. Judges plug in at exactly one place (after the code checks, before the record is written) and they cannot influence the outcome and trajectory columns. `success` is now "outcome and trajectory pass, and no judge *explicitly failed*": `judge_pass is not False`, so a case with no judges, where `judge_pass` is `None`, is not penalized.

One more design point: a judge that errored is counted in `judge_errors` and shows as not passed in the record, but the report calls it out separately with a warning, so a broken judge model is never mistaken for a broken agent.

## 1. Reading the judge list from a case

A case may name a judge as a bare string or with parameters. `judge_specs` normalizes both to `(name, params)`.

```python
def judge_specs(case: dict) -> list[tuple[str, dict]]:
    out = []
    for j in case.get("judges", []):
        out.append((j, {}) if isinstance(j, str) else next(iter(j.items())))
    return out
```

In YAML, `- faithfulness` is a string with no parameters, and `- caution: {needs_disclaimer: true}` is a one-key dictionary. The function handles both.

## 2. Running the judges in `evaluate`

Add the import `from evals.judges.judge import JUDGE_MODEL, build_input, run_judge` to `runner.py`, add the `judge_llm` parameter to `evaluate`, and run the judges after the code checks.

```python
def evaluate(case: dict, rep: int, knowledge, *, model=None, temperature=0.0, seed=42, judge_llm=None) -> dict:
    ctx = execute(case, rep, knowledge, model, temperature, seed)
    outcome = run_outcome(ctx)
    traj = run_trajectory(ctx)

    judges = []
    if judge_llm is not None:
        for name, params in judge_specs(case):
            judges.append((name, run_judge(name, build_input(ctx, params), judge_llm)))
```

If `judge_llm` is `None` (no `--judges` flag) the loop is skipped and `judges` stays empty. Then the pass flags and the record change from placeholders to real values:

```python
    outcome_pass = all(c.passed for c in outcome)
    traj_pass = all(c.passed for c in traj)
    judge_pass = None if not judges else all(j.passed for _, j in judges)
    judge_errors = sum(1 for _, j in judges if j.error)
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
        "judges": [asdict(j) for _, j in judges],
        "outcome_pass": outcome_pass,
        "trajectory_pass": traj_pass,
        "judge_pass": judge_pass,
        "judge_errors": judge_errors,
        "success": outcome_pass and traj_pass and (judge_pass is not False),
        "metrics": metrics(ctx),
        "latency_s": round(ctx.latency_s, 1),
        "agent_model": model or "default",
        "judge_model": JUDGE_MODEL if judges else None,
        "temperature": temperature,
        "seed": seed + rep,
    }
```

`judge_pass` is `None` when no judge ran, `True` when all passed and `False` otherwise. The record also stores which judge model was used, so a report can never be misread as coming from a different judge than it did.

## 3. The `--judges` flag

In `run_suite.py`, add the import (`from evals.judges.judge import get_judge_llm`), the flag, and build the judge model once, next to the knowledge index:

```python
    p.add_argument("--judges", action="store_true", help="also run the LLM judges (slower)")
```

```python
    knowledge = Knowledge()  # index once; every run gets a fresh Market
    judge_llm = get_judge_llm() if args.judges else None
```

Finally pass it into `evaluate`:

```python
                rec = evaluate(case, rep, knowledge, model=args.model, temperature=args.temperature, seed=args.seed, judge_llm=judge_llm)
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

The progress line already prints the names of failed judges next to the failed checks, so a judge failure is visible while the suite is running.

## Try it

Run a mix of cases that have judges, including one you expect the agent to get wrong:

```bash
uv run --group evals python -m evals.run_suite --ids E1,F1,H1 --judges
```

Expected output (timings and the exact failures vary, the structure does not):

```
3 cases x 1 runs -> evals/results/run-....jsonl

PASS  E1   run 1/1   ...
PASS  F1   run 1/1   ...
FAIL  H1   run 1/1   ...  abstention, faithfulness

Results: run-....jsonl   agent=default  judge=llama3:8b  temperature=0.0

By category                runs  outcome traject.  judges  SUCCESS  ...
E: Trading actions            1     100%     100%    100%     100%  ...
F: Rejections                 1     100%     100%    100%     100%  ...
H: Abstention                 1     100%     100%      0%       0%  ...

...
Failures: 1 of 3 runs

  H1 (run 1)  tools: ['search_knowledge']
    x judge:abstention: The answer states specific figures (1% and 0.5%) that are not in the evidence ...
    x judge:faithfulness: 1/2 claims supported. Unsupported: ['It is typically 1% for equity funds and 0.5% for debt funds.']
    answer: 'The exit load on mutual funds is general information and not specific to this assistant. It is typically 1% for equity funds and 0.5% for debt funds.'
```

H1 is the interesting one. The outcome and trajectory columns are 100% (the agent searched the knowledge base, made no trade, did not stop) and the case still fails, because the answer **invented figures that the documents do not contain**. No code check could have caught that. A group in which no case has a `judges:` list shows `-` in the judges column, as in Step 7.

## Checkpoint

This is the final version of both files, replacing the Step 7 versions.

<details>
<summary>Full <code>evals/runner.py</code></summary>

```python
"""Run one case once: fresh sandbox, optional fault, all turns, then outcome / trajectory / judge checks."""

import time
from dataclasses import asdict

from evals.checkers import run_outcome, run_trajectory
from evals.checkers.trajectory import metrics
from evals.context import CaseRun
from evals.faults import apply_fault
from evals.judges.judge import JUDGE_MODEL, build_input, run_judge
from market_assistant import Market, build_agent


def judge_specs(case: dict) -> list[tuple[str, dict]]:
    out = []
    for j in case.get("judges", []):
        out.append((j, {}) if isinstance(j, str) else next(iter(j.items())))
    return out


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


def evaluate(case: dict, rep: int, knowledge, *, model=None, temperature=0.0, seed=42, judge_llm=None) -> dict:
    ctx = execute(case, rep, knowledge, model, temperature, seed)
    outcome = run_outcome(ctx)
    traj = run_trajectory(ctx)

    judges = []
    if judge_llm is not None:
        for name, params in judge_specs(case):
            judges.append((name, run_judge(name, build_input(ctx, params), judge_llm)))

    outcome_pass = all(c.passed for c in outcome)
    traj_pass = all(c.passed for c in traj)
    judge_pass = None if not judges else all(j.passed for _, j in judges)
    judge_errors = sum(1 for _, j in judges if j.error)
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
        "judges": [asdict(j) for _, j in judges],
        "outcome_pass": outcome_pass,
        "trajectory_pass": traj_pass,
        "judge_pass": judge_pass,
        "judge_errors": judge_errors,
        "success": outcome_pass and traj_pass and (judge_pass is not False),
        "metrics": metrics(ctx),
        "latency_s": round(ctx.latency_s, 1),
        "agent_model": model or "default",
        "judge_model": JUDGE_MODEL if judges else None,
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
    uv run --group evals python -m evals.run_suite --ids A1,E1 --judges  # specific cases, with LLM judges
    uv run --group evals python -m evals.run_suite --category E,F -k 5 --temperature 0.4   # reliability (pass^k)

With temperature 0 the repeated runs are (nearly) identical; use --temperature > 0 with -k > 1 to measure reliability.
"""

import argparse
import json
import time
from pathlib import Path

import yaml

from evals.judges.judge import get_judge_llm
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
    p.add_argument("--judges", action="store_true", help="also run the LLM judges (slower)")
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
    judge_llm = get_judge_llm() if args.judges else None
    args.out.mkdir(exist_ok=True)
    path = args.out / f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"

    print(f"{len(cases)} cases x {args.k} runs -> {path}\n")
    with path.open("w") as f:
        for case in cases:
            for rep in range(args.k):
                rec = evaluate(case, rep, knowledge, model=args.model, temperature=args.temperature, seed=args.seed, judge_llm=judge_llm)
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

Both match [../evals/runner.py](../evals/runner.py) and [../evals/run_suite.py](../evals/run_suite.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Judge column stays `-` | Forgot `--judges`, or the case has no `judges:` list | Pass the flag; add judges to the case in `cases.yaml` |
| `KeyError` in `judge_specs` or `run_judge` | Misspelled judge name in the YAML | Names must be keys of `JUDGES`: `faithfulness`, `abstention`, `honest_reporting`, `caution`, `reference_correct` |
| `reference_correct` always fails | The case has no `reference` parameter | Give it `reference_correct: {reference: "..."}` |
| The report warns about judge errors | The judge model failed to return a valid verdict | Check Ollama and the model; errored judges are counted as not passed, never as passed |
| Everything judged is slow | One model call per judge per case | Run judges only on the categories you are changing; cached verdicts make re-runs free |

Next: **[Calibrating the Judges](11-calibrating-the-judges.md)**.
