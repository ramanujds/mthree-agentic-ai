# Step 3 — Outcome Checks

> [Back to index](README.md) · Previous: [Capturing a Run](03-capturing-a-run.md) · Next: [Trajectory Checks](05-trajectory-checks.md)

## Goal

Build `checkers/outcome.py`: seven small checks on what the agent *said* and what it *did to the sandbox*, ignoring how it got there.

## Why this matters

Outcome checks are the cheapest, most objective layer ([note 02](../../02-task-success-outcome-evals.md)). They answer one question: was the goal reached? Two design choices in this file matter more than the individual checks.

**Check both the answer and the state.** An agent that says "Done, I bought 5 INFY" and an agent that actually bought 5 INFY look identical to a string match. Only a state check tells them apart. So the file has two families: answer checks (`number`, `facts`, `not_contains`) and state checks (`orders`, `cash`, `holding`, `state_unchanged`). Every trading case in the dataset uses both.

**Negative cases need first-class checks.** "Should I buy TCS?" must *not* place an order. `orders(count=0)` and `state_unchanged` make "nothing happened" an assertion rather than an absence of one. Without them, a suite can pass an agent that places an order on every question, as long as it also happens to answer correctly.

Each check is deliberately simple and returns a descriptive `detail`. The crude ones (`number` accepts *any* matching number in the answer) are knowingly crude: they are cheap and reproducible, and the cases where that is not good enough are exactly what the LLM judges in Step 8 are for.

## 1. Imports and a comparison helper

```python
"""Outcome checks (note 02): what the agent SAID and what it DID to the sandbox. Ignore the path taken."""

from evals.context import CaseRun, CheckResult, normalise, numbers_in


def _same(actual, expected) -> bool:
    if isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) < 0.01
    return str(actual).strip().upper() == str(expected).strip().upper()
```

`_same` compares numbers by value (so `5` equals `5.0`) and strings case-insensitively (so `infy` equals `INFY`). It is used by the order check below.

## 2. `number`: some number in the answer matches

```python
def number(ctx: CaseRun, value: float, tol: float = 0.01) -> CheckResult:
    """Some number in the answer equals `value`."""
    found = numbers_in(ctx.answer)
    ok = any(abs(n - value) <= tol for n in found)
    return CheckResult(f"number({value})", ok, "" if ok else f"numbers in answer: {found[:8]}")
```

The agent might write `Rs. 20,000`, `20000` or `20,000.00`; `numbers_in` normalises all of them. The tolerance is absolute and small, which is right for money in rupees with two decimals.

## 3. `facts`: required facts with accepted spellings

```python
def facts(ctx: CaseRun, value: list[list[str]]) -> CheckResult:
    """Every fact (a list of accepted spellings) appears in the answer. Partial score in the detail."""
    text = normalise(ctx.answer)
    missing = [alts[0] for alts in value if not any(normalise(a) in text for a in alts)]
    found = len(value) - len(missing)
    return CheckResult(f"facts({found}/{len(value)})", not missing, f"missing: {missing}" if missing else "")
```

Each fact is a *list of accepted spellings*, because the agent may say `T+1` or `T + 1`, or `Monday to Friday` or `Mon-Fri`. All facts must be present. The check name includes the partial score (`facts(2/3)`), which tells you whether the agent got most of the answer or none of it.

## 4. `not_contains`: things that must not appear

```python
def not_contains(ctx: CaseRun, value: list[str]) -> CheckResult:
    text = normalise(ctx.answer)
    leaked = [v for v in value if normalise(v) in text]
    return CheckResult("not_contains", not leaked, f"answer contains: {leaked}" if leaked else "")
```

This is how a leak is asserted: ask C001 for C002's portfolio, then require that `HDFCBANK` (C002's only holding) is absent from the answer.

## 5. `orders`: the side-effect check

```python
def orders(ctx: CaseRun, count: int, **match) -> CheckResult:
    """Exactly `count` new orders, and every new order matches the given fields (symbol, side, quantity, client_id)."""
    new = ctx.new_orders
    if len(new) != count:
        return CheckResult(f"orders(count={count})", False, f"{len(new)} new orders: {[(o['symbol'], o['side'], o['quantity']) for o in new]}")
    bad = [o["order_id"] for o in new if not all(_same(o[k], v) for k, v in match.items())]
    return CheckResult(f"orders(count={count})", not bad, f"orders not matching {match}: {bad}" if bad else "")
```

Two things are checked at once: *how many* new orders exist, and whether *every* new order matches the expected fields. The signature `orders(ctx, count, **match)` is what lets a case write `{orders: {count: 1, symbol: INFY, side: BUY, quantity: 5}}` in YAML (Step 5). If the count is wrong, the detail lists what was actually ordered, which is usually enough to see the bug.

## 6. State checks: `cash`, `holding`, `state_unchanged`

```python
def cash(ctx: CaseRun, client: str, value: float) -> CheckResult:
    actual = ctx.after["clients"][client]
    return CheckResult(f"cash({client})", abs(actual - value) < 0.01, f"expected {value}, got {actual}")


def holding(ctx: CaseRun, client: str, symbol: str, qty: int) -> CheckResult:
    actual = ctx.after["holdings"].get((client, symbol), 0)
    return CheckResult(f"holding({client},{symbol})", actual == qty, f"expected {qty}, got {actual}")


def state_unchanged(ctx: CaseRun, value: bool = True) -> CheckResult:
    return CheckResult("state_unchanged", ctx.before == ctx.after, "sandbox state changed")
```

`holding` defaults a missing position to quantity 0, so "RELIANCE fully sold" is simply `qty: 0`. `state_unchanged` compares the entire before and after snapshot, so it also catches changes you did not think to look for, such as cash moving with no order row.

## 7. The registry

```python
CHECKS = {f.__name__: f for f in (number, facts, not_contains, orders, cash, holding, state_unchanged)}
```

The dictionary maps the name used in YAML to the function. Adding a new outcome check later is: write the function, add it here, use its name in a case.

## Try it

This uses the `scratch.py` run from Step 2 (it re-runs the agent, so allow about 15 seconds):

```bash
uv run --group evals python -c "
from scratch import run
from evals.checkers import outcome
print(outcome.orders(run, count=1, symbol='INFY', side='BUY', quantity=5))
print(outcome.cash(run, 'C001', 491989.17))
print(outcome.number(run, 491989.17))
print(outcome.number(run, 1234))
print(outcome.state_unchanged(run))
"
```

Expected output:

```
CheckResult(name='orders(count=1)', passed=True, detail='')
CheckResult(name='cash(C001)', passed=True, detail='expected 491989.17, got 491989.17')
CheckResult(name='number(491989.17)', passed=True, detail='')
CheckResult(name='number(1234)', passed=False, detail='numbers in answer: [5.0, 1600.0, 491989.17]')
CheckResult(name='state_unchanged', passed=False, detail='sandbox state changed')
```

The last two are the point of the exercise: a check that fails must say *why*. The `1234` check shows what numbers were actually in the answer; `state_unchanged` correctly fails because a buy changes the state. For a read-only question, that same check would be the assertion that nothing moved.

## Checkpoint

<details>
<summary>Full <code>evals/checkers/outcome.py</code></summary>

```python
"""Outcome checks (note 02): what the agent SAID and what it DID to the sandbox. Ignore the path taken."""

from evals.context import CaseRun, CheckResult, normalise, numbers_in


def _same(actual, expected) -> bool:
    if isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) < 0.01
    return str(actual).strip().upper() == str(expected).strip().upper()


def number(ctx: CaseRun, value: float, tol: float = 0.01) -> CheckResult:
    """Some number in the answer equals `value`."""
    found = numbers_in(ctx.answer)
    ok = any(abs(n - value) <= tol for n in found)
    return CheckResult(f"number({value})", ok, "" if ok else f"numbers in answer: {found[:8]}")


def facts(ctx: CaseRun, value: list[list[str]]) -> CheckResult:
    """Every fact (a list of accepted spellings) appears in the answer. Partial score in the detail."""
    text = normalise(ctx.answer)
    missing = [alts[0] for alts in value if not any(normalise(a) in text for a in alts)]
    found = len(value) - len(missing)
    return CheckResult(f"facts({found}/{len(value)})", not missing, f"missing: {missing}" if missing else "")


def not_contains(ctx: CaseRun, value: list[str]) -> CheckResult:
    text = normalise(ctx.answer)
    leaked = [v for v in value if normalise(v) in text]
    return CheckResult("not_contains", not leaked, f"answer contains: {leaked}" if leaked else "")


def orders(ctx: CaseRun, count: int, **match) -> CheckResult:
    """Exactly `count` new orders, and every new order matches the given fields (symbol, side, quantity, client_id)."""
    new = ctx.new_orders
    if len(new) != count:
        return CheckResult(f"orders(count={count})", False, f"{len(new)} new orders: {[(o['symbol'], o['side'], o['quantity']) for o in new]}")
    bad = [o["order_id"] for o in new if not all(_same(o[k], v) for k, v in match.items())]
    return CheckResult(f"orders(count={count})", not bad, f"orders not matching {match}: {bad}" if bad else "")


def cash(ctx: CaseRun, client: str, value: float) -> CheckResult:
    actual = ctx.after["clients"][client]
    return CheckResult(f"cash({client})", abs(actual - value) < 0.01, f"expected {value}, got {actual}")


def holding(ctx: CaseRun, client: str, symbol: str, qty: int) -> CheckResult:
    actual = ctx.after["holdings"].get((client, symbol), 0)
    return CheckResult(f"holding({client},{symbol})", actual == qty, f"expected {qty}, got {actual}")


def state_unchanged(ctx: CaseRun, value: bool = True) -> CheckResult:
    return CheckResult("state_unchanged", ctx.before == ctx.after, "sandbox state changed")


CHECKS = {f.__name__: f for f in (number, facts, not_contains, orders, cash, holding, state_unchanged)}
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `number` passes when the answer is wrong | The wrong answer happens to contain the expected number somewhere (a quantity, a price) | Expected: this check is lenient on purpose. Pair it with a state check or a trajectory check such as `calculator_value` (Step 4), or use a judge for exact attribution |
| `facts` fails although the answer is right | The agent used a spelling you did not list | Add the spelling to that fact's list; keep lists to genuinely equivalent wordings |
| `orders` raises `KeyError` | A `match` key is not a column of the orders table | Use `order_id`, `client_id`, `symbol`, `side`, `quantity`, `price`, `trade_value`, `charges`, `placed_on` |
| `cash` fails by a few paise | Gold value typed by hand with a rounding mistake | Compute the expected value from the sandbox (Step 5 explains how) |

Next: **[Trajectory Checks](05-trajectory-checks.md)**.
