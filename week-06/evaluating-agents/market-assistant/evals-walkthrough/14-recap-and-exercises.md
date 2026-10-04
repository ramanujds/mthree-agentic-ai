# Step 13 — Recap and Exercises

> [Back to index](README.md) · Previous: [Reliability and Reading Results](13-reliability-and-reading-results.md)

## What you built

An eval harness that runs a golden dataset against an agent in a fresh sandbox per run and scores every run three independent ways:

- **Outcome** (code): did the answer and the sandbox end up right?
- **Trajectory** (code): did the tool calls follow the rules, with universal checks on every case?
- **Judge** (model): is the wording faithful, honest, appropriately careful, and is the judge itself trustworthy?

Plus fault injection, calibration against human labels, tests for the harness itself, and a report that surfaces reliability, cost and every failure.

## Quick reference card

| Concept | Where it lives |
| --- | --- |
| One run's record, and the state diff | `CaseRun` in [../evals/context.py](../evals/context.py) |
| Answer and state checks | [../evals/checkers/outcome.py](../evals/checkers/outcome.py) |
| Tool-call rules, universal checks, metrics | [../evals/checkers/trajectory.py](../evals/checkers/trajectory.py) |
| YAML check to function call | `run_spec` in [../evals/checkers/__init__.py](../evals/checkers/__init__.py) |
| The golden dataset | [../evals/datasets/cases.yaml](../evals/datasets/cases.yaml) |
| Breaking a tool on purpose | [../evals/faults.py](../evals/faults.py) |
| Run one case in a fresh sandbox | `execute` / `evaluate` in [../evals/runner.py](../evals/runner.py) |
| Run many, save JSONL | [../evals/run_suite.py](../evals/run_suite.py) |
| Summaries, pass@k, pass^k, failures | [../evals/report.py](../evals/report.py) |
| Rubrics and verdict models | [../evals/judges/rubrics.py](../evals/judges/rubrics.py) |
| Running a judge, caching, errors | [../evals/judges/judge.py](../evals/judges/judge.py) |
| Judge vs human labels | [../evals/judges/calibrate.py](../evals/judges/calibrate.py), [calibration.yaml](../evals/judges/calibration.yaml) |
| Tests for the harness | [../evals/tests/](../evals/tests/) |

## Gotchas

| Gotcha | Why it bites |
| --- | --- |
| Forgetting `--group evals` | Every eval command needs the extra dependency group; the error looks like a missing module |
| Reusing a sandbox between runs | Cases contaminate each other and results depend on execution order |
| `temperature 0` with `-k` above 1 | Repeated runs are identical, so pass^k flatters the agent |
| The `number` check is lenient | Any matching number in the answer passes; back it with a state or trajectory check |
| Treating `stopped` as success | The agent's "exceeded max_steps" text reads like a polite answer; `not_stopped` makes it a failure |
| Judge is the same model as the agent | Self-preference plus a weak judge; calibrate it and trust code-checked columns more |
| A failed judge counted as a verdict | Makes a flaky judge look like an agent regression; errors are reported separately |
| Typing gold values by hand | A wrong expectation blames the agent for your arithmetic; compute from the sandbox and test it |
| One run per case | One draw from a noisy process is not a rate |
| Averaging the three scores | Hides which dimension regressed; keep them as separate columns |

## Discussion questions

1. Case I5 expects zero orders after a timeout on the first `place_order` call, but in a real system the order may have executed. How would the case and the fault change to model "timed out but did execute", and what would the right agent behaviour be then?
2. `number` passes if *any* number in the answer matches. Describe an agent failure that slips through it, then name the cheapest additional check that would catch it.
3. Why are `not_stopped` and `client_scope` universal checks rather than lines in each case? What would happen to the suite over a year if they were opt-in?
4. The abstention judge passed an invented answer. List three different responses (rubric, data, model, process) and say which you would try first and why.
5. Trajectory checks are constraints rather than expected sequences. Give an example of a task with two valid paths where an exact-match check would fail a correct agent.

## Exercises

Ordered easiest to hardest. Keep exercise changes on a branch or copy so the reference stays matched.

1. **Add a case from a failure.** Run a few questions of your own through the agent until it does something wrong, then write a case that catches it (`outcome` plus `trajectory`), and confirm it fails. Fix nothing; the point is that the failure is now permanent.
2. **Add an outcome check.** Write `number_between(ctx, low, high)` in `checkers/outcome.py`, register it in `CHECKS`, add a unit test in `test_checkers.py`, and use it in a case where the exact value does not matter (for example, a quote that lies within the day's high and low).
3. **Add a fault.** Add `calculator_wrong` to `faults.py`: a calculator that returns a wrong number once. Write a case that expects the final answer to be right anyway, and a judge or trajectory check that detects whether the agent noticed. What does your agent do?
4. **Add a judge.** Add a `tone` judge to `rubrics.py` and `judge.py` (a boolean: is the answer polite and free of jargon?). Add four planted examples to `calibration.yaml`, run calibration, and report its TNR.
5. **Pairwise comparison.** Write `compare.py` that takes two results files, finds the cases present in both, and asks a judge which answer is better, in both orders, recording a tie when the two orders disagree. Use it to compare `llama3:8b` against another model, or the same model with a changed agent prompt.
6. **Rebuild from memory.** Delete `checkers/trajectory.py`, then rewrite it from memory using only the Step 4 introduction as a guide, run the tests from Step 11 against it, and diff it against [../evals/checkers/trajectory.py](../evals/checkers/trajectory.py). Every difference is either an equivalent style choice or a bug you just found.

## What's next

This walkthrough covered three of the evaluation approaches. The remaining ones from the notes are [human evaluation](../../05-human-evaluation.md), which supplies the labels that make Step 10's calibration real, and [benchmarks and golden datasets](../../06-benchmarks-and-golden-datasets.md), which go deeper on building and maintaining the dataset from Step 5. Natural extensions of this harness are CI wiring (run the code-only subset on every change, the full suite nightly) and production monitoring.
