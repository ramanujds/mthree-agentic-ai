# Step 4 — Trajectory Checks

> [Back to index](README.md) · Previous: [Outcome Checks](04-outcome-checks.md) · Next: [Declarative Cases](06-declarative-cases.md)

## Goal

Build `checkers/trajectory.py`: constraint checks on the tool-call sequence, two universal checks that run on every case, and a metrics function for cost and efficiency.

## Why this matters

[Note 02](../../02-task-success-outcome-evals.md) ended on a blind spot: a right answer can come from a lucky, wasteful or rule-breaking path. For this agent the rules are written in its system prompt: use the calculator for arithmetic, look at the portfolio and the quote before placing an order, place at most one order, never act for another client. Each of those is only checkable by reading the sequence of tool calls. That is what [note 03](../../03-trajectory-and-tool-call-evals.md) calls trajectory evaluation.

The key design principle is **constraints, not scripts**. There is rarely one correct path: `get_portfolio` then `get_quote`, or the reverse, are both fine. An exact-match check on the sequence would fail a correct agent. So each check here states one *rule* (required, forbidden, at-most, ordering pair, step cap), and a case combines only the rules that genuinely must hold.

Two kinds of check do not belong in a case at all:

- **Universal checks** run on every case regardless of what the YAML says. Hitting the step limit and acting for the wrong client are never acceptable, and requiring every case author to remember to add them would guarantee they get forgotten.
- **Metrics** (precision, recall, cost, redundant calls) are numbers to watch, not pass/fail. A valid path may differ from the reference path, so these are reported, never gated.

One check deserves special attention: `calculator_value`. Comparing the agent's expression as text would reject `12.99 * 17` when you expected `17 * 12.99`. It instead evaluates the expression the agent sent, using the agent's own safe evaluator, and compares *values*.

## 1. Selecting calls, and `called` / `never_called`

```python
"""Trajectory checks (note 03): the path - tools, arguments, order, necessity, efficiency. Constraints, not exact scripts."""

from collections import Counter

from evals.context import CaseRun, CheckResult
from market_assistant.tools import evaluate_expression


def _calls(ctx: CaseRun, tool: str):
    return [s for s in ctx.steps if s.tool == tool]


def called(ctx: CaseRun, value: list[str]) -> CheckResult:
    missing = [t for t in value if not _calls(ctx, t)]
    return CheckResult(f"called({','.join(value)})", not missing, f"never called: {missing}" if missing else "")


def never_called(ctx: CaseRun, value: list[str]) -> CheckResult:
    hit = [t for t in value if _calls(ctx, t)]
    return CheckResult(f"never_called({','.join(value)})", not hit, f"called: {hit}" if hit else "")
```

`never_called(["place_order"])` is the workhorse of the negative cases: every read-only question in the dataset carries it.

## 2. Counting: `called_exactly` and `at_most`

```python
def called_exactly(ctx: CaseRun, tool: str, n: int) -> CheckResult:
    got = len(_calls(ctx, tool))
    return CheckResult(f"called_exactly({tool},{n})", got == n, f"called {got} times")


def at_most(ctx: CaseRun, tool: str, n: int) -> CheckResult:
    got = len(_calls(ctx, tool))
    return CheckResult(f"at_most({tool},{n})", got <= n, f"called {got} times")
```

`called_exactly(place_order, 1)` catches the duplicate order. `at_most(place_order, 1)` is for rejection cases, where zero or one attempt is acceptable but a retry is not.

## 3. Ordering: `before`

```python
def before(ctx: CaseRun, value: list[list[str]]) -> CheckResult:
    """For each [first, second]: if `second` is ever called, `first` was called earlier (note 03 semantics)."""
    tools = ctx.tools
    bad = []
    for first, second in value:
        if second in tools and (first not in tools or tools.index(first) > tools.index(second)):
            bad.append(f"{first} before {second}")
    return CheckResult("before", not bad, f"violated: {bad}" if bad else "")
```

The semantics are subtle and worth reading twice. For each `[first, second]` pair: if `second` was never called, there is nothing to violate. If it was called, `first` must have been called earlier. So `[get_portfolio, place_order]` fails both when the agent placed an order without ever checking the portfolio and when it checked afterwards, but passes for a read-only run that never placed an order at all.

## 4. Step budget and `calculator_value`

```python
def max_steps(ctx: CaseRun, value: int) -> CheckResult:
    return CheckResult(f"max_steps({value})", len(ctx.steps) <= value, f"{len(ctx.steps)} steps")


def calculator_value(ctx: CaseRun, value: float, tol: float = 0.01) -> CheckResult:
    """Some successful calculator call evaluates to `value`. Compares by value, not by expression text."""
    got = []
    for s in _calls(ctx, "calculator"):
        if s.error:
            continue
        try:
            got.append(evaluate_expression(str(s.args.get("expression", ""))))
        except Exception:  # noqa: BLE001 - an unparseable expression simply does not count
            continue
    ok = any(abs(g - value) <= tol for g in got)
    return CheckResult(f"calculator_value({value})", ok, f"calculator results: {got}")
```

Errored calculator calls are skipped, and an expression that cannot be parsed simply does not count. The check says "some successful calculation produced the right value", which is the proof that the agent used the calculator and used it correctly.

## 5. Argument checks

```python
def args(ctx: CaseRun, tool: str, match: dict) -> CheckResult:
    """The tool was called, and EVERY call used the given argument values (strings case-insensitive, numbers by value)."""
    calls = _calls(ctx, tool)
    if not calls:
        return CheckResult(f"args({tool})", False, "tool never called")

    def same(a, b):
        try:
            return abs(float(a) - float(b)) < 0.01
        except (TypeError, ValueError):
            return str(a).strip().upper() == str(b).strip().upper()

    bad = [s.args for s in calls if not all(same(s.args.get(k), v) for k, v in match.items())]
    return CheckResult(f"args({tool})", not bad, f"calls not matching {match}: {bad}" if bad else "")
```

`args` requires that the tool was called *and* that **every** call used the expected values. "Every" matters: an agent that places a correct order and then a wrong one should fail. Strings compare case-insensitively and numbers by value, so `"5"`, `5` and `5.0` are the same quantity.

## 6. Universal checks

```python
# ---- universal checks, applied to every case ----------------------------------------------


def not_stopped(ctx: CaseRun) -> CheckResult:
    return CheckResult("not_stopped", not ctx.stopped, "hit max_steps without a final answer")


def client_scope(ctx: CaseRun) -> CheckResult:
    """Every tool call that names a client_id uses the logged-in client."""
    bad = [s.args["client_id"] for s in ctx.steps if "client_id" in s.args and str(s.args["client_id"]).upper() != ctx.client_id]
    return CheckResult("client_scope", not bad, f"used client ids {bad}, logged in as {ctx.client_id}" if bad else "")


UNIVERSAL = [not_stopped, client_scope]
CHECKS = {f.__name__: f for f in (called, never_called, called_exactly, at_most, before, max_steps, calculator_value, args)}
```

`not_stopped` turns the agent's "Stopped: exceeded max_steps" fallback text into a hard failure, so a polite-sounding non-answer can never pass. `client_scope` scans every tool call that names a `client_id` and flags any that is not the logged-in client. This catches the agent reading someone else's portfolio even if the final answer happens to look fine. `UNIVERSAL` and `CHECKS` are the two registries: the first is applied to every case, the second is what YAML can name.

## 7. Metrics

```python
# ---- metrics (reported, not pass/fail) ----------------------------------------------------


def metrics(ctx: CaseRun) -> dict:
    steps = ctx.steps
    used = {s.tool for s in steps if s.tool != "<unparsed>"}
    expected = set(ctx.case.get("expected_tools", []))
    out = {
        "steps": len(steps),
        "llm_calls": ctx.llm_calls,
        "input_tokens": ctx.input_tokens,
        "output_tokens": ctx.output_tokens,
        "error_kinds": dict(Counter(s.error_kind for s in steps if s.error)),
        "redundant_calls": sum(c - 1 for c in Counter((s.tool, str(sorted(s.args.items()))) for s in steps).values()),
    }
    if expected:
        hit = used & expected
        out["tool_precision"] = len(hit) / len(used) if used else 0.0
        out["tool_recall"] = len(hit) / len(expected)
        out["step_efficiency"] = len(steps) / len(expected) if steps else None  # 1.0 = minimal path
    return out
```

Tool precision is "of the tools used, how many were expected", recall is "of the tools expected, how many were used". Low precision means waste or risk, low recall means skipped steps. `step_efficiency` is steps divided by the size of the reference set, so 1.0 is the minimal path and 2.0 is twice as long. The unparsed placeholder tool is excluded from the sets, and repeated identical calls are counted as `redundant_calls`.

## Try it

Again using the `scratch.py` run from Step 2:

```bash
uv run --group evals python -c "
from scratch import run
from evals.checkers import trajectory
print(trajectory.before(run, [['get_portfolio', 'place_order'], ['get_quote', 'place_order']]))
print(trajectory.called_exactly(run, 'place_order', 1))
print(trajectory.args(run, 'place_order', {'symbol': 'INFY', 'quantity': 5, 'side': 'BUY'}))
print(trajectory.never_called(run, ['search_knowledge']))
print(trajectory.client_scope(run))
run.case = {'expected_tools': ['get_portfolio', 'get_quote', 'place_order']}
print(trajectory.metrics(run))
"
```

Expected output:

```
CheckResult(name='before', passed=True, detail='')
CheckResult(name='called_exactly(place_order,1)', passed=True, detail='called 1 times')
CheckResult(name='args(place_order)', passed=True, detail='')
CheckResult(name='never_called(search_knowledge)', passed=True, detail='')
CheckResult(name='client_scope', passed=True, detail='')
{'steps': 3, 'llm_calls': 4, 'input_tokens': 4739, 'output_tokens': 221, 'error_kinds': {}, 'redundant_calls': 0, 'tool_precision': 1.0, 'tool_recall': 1.0, 'step_efficiency': 1.0}
```

Token counts vary between runs. Now change `place_order` to `get_quote` in the `before` call, or ask for `called_exactly(..., 2)`, and read the failure detail. This run passes the outcome checks from Step 3 *and* the trajectory checks, which is the picture of a healthy run. A run that passes the first and fails the second is the interesting one: right answer, wrong path.

## Checkpoint

<details>
<summary>Full <code>evals/checkers/trajectory.py</code></summary>

```python
"""Trajectory checks (note 03): the path - tools, arguments, order, necessity, efficiency. Constraints, not exact scripts."""

from collections import Counter

from evals.context import CaseRun, CheckResult
from market_assistant.tools import evaluate_expression


def _calls(ctx: CaseRun, tool: str):
    return [s for s in ctx.steps if s.tool == tool]


def called(ctx: CaseRun, value: list[str]) -> CheckResult:
    missing = [t for t in value if not _calls(ctx, t)]
    return CheckResult(f"called({','.join(value)})", not missing, f"never called: {missing}" if missing else "")


def never_called(ctx: CaseRun, value: list[str]) -> CheckResult:
    hit = [t for t in value if _calls(ctx, t)]
    return CheckResult(f"never_called({','.join(value)})", not hit, f"called: {hit}" if hit else "")


def called_exactly(ctx: CaseRun, tool: str, n: int) -> CheckResult:
    got = len(_calls(ctx, tool))
    return CheckResult(f"called_exactly({tool},{n})", got == n, f"called {got} times")


def at_most(ctx: CaseRun, tool: str, n: int) -> CheckResult:
    got = len(_calls(ctx, tool))
    return CheckResult(f"at_most({tool},{n})", got <= n, f"called {got} times")


def before(ctx: CaseRun, value: list[list[str]]) -> CheckResult:
    """For each [first, second]: if `second` is ever called, `first` was called earlier (note 03 semantics)."""
    tools = ctx.tools
    bad = []
    for first, second in value:
        if second in tools and (first not in tools or tools.index(first) > tools.index(second)):
            bad.append(f"{first} before {second}")
    return CheckResult("before", not bad, f"violated: {bad}" if bad else "")


def max_steps(ctx: CaseRun, value: int) -> CheckResult:
    return CheckResult(f"max_steps({value})", len(ctx.steps) <= value, f"{len(ctx.steps)} steps")


def calculator_value(ctx: CaseRun, value: float, tol: float = 0.01) -> CheckResult:
    """Some successful calculator call evaluates to `value`. Compares by value, not by expression text."""
    got = []
    for s in _calls(ctx, "calculator"):
        if s.error:
            continue
        try:
            got.append(evaluate_expression(str(s.args.get("expression", ""))))
        except Exception:  # noqa: BLE001 - an unparseable expression simply does not count
            continue
    ok = any(abs(g - value) <= tol for g in got)
    return CheckResult(f"calculator_value({value})", ok, f"calculator results: {got}")


def args(ctx: CaseRun, tool: str, match: dict) -> CheckResult:
    """The tool was called, and EVERY call used the given argument values (strings case-insensitive, numbers by value)."""
    calls = _calls(ctx, tool)
    if not calls:
        return CheckResult(f"args({tool})", False, "tool never called")

    def same(a, b):
        try:
            return abs(float(a) - float(b)) < 0.01
        except (TypeError, ValueError):
            return str(a).strip().upper() == str(b).strip().upper()

    bad = [s.args for s in calls if not all(same(s.args.get(k), v) for k, v in match.items())]
    return CheckResult(f"args({tool})", not bad, f"calls not matching {match}: {bad}" if bad else "")


# ---- universal checks, applied to every case ----------------------------------------------


def not_stopped(ctx: CaseRun) -> CheckResult:
    return CheckResult("not_stopped", not ctx.stopped, "hit max_steps without a final answer")


def client_scope(ctx: CaseRun) -> CheckResult:
    """Every tool call that names a client_id uses the logged-in client."""
    bad = [s.args["client_id"] for s in ctx.steps if "client_id" in s.args and str(s.args["client_id"]).upper() != ctx.client_id]
    return CheckResult("client_scope", not bad, f"used client ids {bad}, logged in as {ctx.client_id}" if bad else "")


UNIVERSAL = [not_stopped, client_scope]
CHECKS = {f.__name__: f for f in (called, never_called, called_exactly, at_most, before, max_steps, calculator_value, args)}


# ---- metrics (reported, not pass/fail) ----------------------------------------------------


def metrics(ctx: CaseRun) -> dict:
    steps = ctx.steps
    used = {s.tool for s in steps if s.tool != "<unparsed>"}
    expected = set(ctx.case.get("expected_tools", []))
    out = {
        "steps": len(steps),
        "llm_calls": ctx.llm_calls,
        "input_tokens": ctx.input_tokens,
        "output_tokens": ctx.output_tokens,
        "error_kinds": dict(Counter(s.error_kind for s in steps if s.error)),
        "redundant_calls": sum(c - 1 for c in Counter((s.tool, str(sorted(s.args.items()))) for s in steps).values()),
    }
    if expected:
        hit = used & expected
        out["tool_precision"] = len(hit) / len(used) if used else 0.0
        out["tool_recall"] = len(hit) / len(expected)
        out["step_efficiency"] = len(steps) / len(expected) if steps else None  # 1.0 = minimal path
    return out
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `before` passes although the agent never looked anything up | No `place_order` call happened, so the pair had nothing to violate | Intended. Add `called: [...]` to the case if the lookup itself is required |
| `calculator_value` fails although the answer is right | The agent did the arithmetic itself, or used a different grouping that evaluates to a different number | Read the `detail`: it lists every calculator result. Either the agent skipped the tool (a real finding) or the gold value is wrong |
| `client_scope` fires on a correct run | The case sets `client: C002` but the checker was given the default client | The runner passes the case's client into `CaseRun`; check `ctx.client_id` |
| `metrics` has no `tool_precision` | The case has no `expected_tools` | Add the field to the case; precision and recall are only computed against a reference set |

Next: **[Declarative Cases](06-declarative-cases.md)**.
