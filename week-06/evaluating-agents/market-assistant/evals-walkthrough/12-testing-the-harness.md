# Step 11 — Testing the Harness

> [Back to index](README.md) · Previous: [Calibrating the Judges](11-calibrating-the-judges.md) · Next: [Reliability and Reading Results](13-reliability-and-reading-results.md)

## Goal

Write `tests/test_checkers.py` and `tests/test_cases.py`: fast tests, with no model involved, that prove the checkers behave as intended and that the dataset is well-formed and its gold numbers match the sandbox.

## Why this matters

An eval harness fails silently, and the silent failures are the worst kind. A checker that always passes makes the agent look perfect. A checker that always fails sends you hunting for an agent bug that does not exist. A typo in a YAML check name crashes a run an hour in. Nothing in the suite tells you the *harness* is wrong, because the harness is the thing doing the telling.

Two properties make this cheap to fix:

- **Checkers are pure functions of a recorded run** (Step 2). A test builds a `CaseRun` by hand, with chosen steps and answers, and asserts the verdict. No agent, no Ollama, no waiting; the whole suite of tests runs in about two seconds.
- **The dataset is data**, so it can be validated mechanically: unique ids, known categories, check names that exist, fault and judge names that exist.

The most valuable test is the one that recomputes the gold numbers. If someone edits the seed data (say, changes the brokerage rate), the expected cash values in category E silently become wrong, and the agent gets blamed. A test that places each trade in the sandbox and compares to the YAML turns that into a loud, immediate, specific failure.

Write tests for the properties you have been bitten by, not for line coverage. Each test below pins a behaviour from earlier steps that is easy to get subtly wrong.

## 1. Building runs by hand

Create `evals/tests/test_checkers.py`. A tiny factory builds a `CaseRun` from just the parts a test cares about.

```python
"""Tests for the eval harness itself: a checker that is wrong is worse than no checker."""

import pytest

from evals.checkers import outcome, trajectory
from evals.context import CaseRun, numbers_in
from market_assistant import RunResult, Step, Trajectory
from market_assistant.market import Market


def make_run(answer="", steps=(), before=None, after=None, stopped=False, client="C001", case=None) -> CaseRun:
    traj = Trajectory(goal="g", steps=list(steps), final_answer=answer)
    result = RunResult(answer=answer, trajectory=traj, retrieved_context=[], stopped=stopped)
    snap = Market().snapshot()
    return CaseRun(case or {}, client, ["q"], [result], before or snap, after or snap)


def step(tool, **args):
    return Step(tool=tool, args=args)
```

`make_run` defaults the sandbox snapshots to a pristine market, so tests that do not care about state still get valid ones, and `step` makes tool calls terse.

## 2. Outcome checks

```python
def test_numbers_in_handles_commas_and_rupee_text():
    assert 220.83 in numbers_in("17 * 12.99 = Rs. 220.83.")
    assert 125000.0 in numbers_in("exempt up to Rs. 1,25,000")


def test_number_check():
    assert outcome.number(make_run("P&L is Rs. 20,000."), 20000).passed
    assert not outcome.number(make_run("P&L is Rs. 2,000."), 20000).passed


def test_facts_accepts_alternatives_and_comma_formats():
    run = make_run("LTCG is 12.5% above Rs. 1,25,000.")
    assert outcome.facts(run, [["12.5"], ["125000", "1.25 lakh"]]).passed
    assert not outcome.facts(run, [["20%"]]).passed


def test_orders_check_counts_and_matches_fields():
    market = Market()
    before = market.snapshot()
    market.place_order("C001", "INFY", 5, "BUY")
    run = make_run(before=before, after=market.snapshot())
    assert outcome.orders(run, count=1, symbol="infy", side="BUY", quantity=5).passed
    assert not outcome.orders(run, count=0).passed
    assert not outcome.orders(run, count=1, quantity=6).passed


def test_state_unchanged_detects_a_trade():
    market = Market()
    before = market.snapshot()
    assert outcome.state_unchanged(make_run(before=before, after=market.snapshot())).passed
    market.place_order("C001", "ITC", 1, "BUY")
    assert not outcome.state_unchanged(make_run(before=before, after=market.snapshot())).passed
```

The order and state-diff tests use the real `Market` to produce genuine before/after snapshots: place a trade, then assert the checker sees it. This is cheap and avoids hand-writing snapshot dictionaries.

## 3. Trajectory checks

```python
def test_before_requires_first_when_second_present():
    ok = make_run(steps=[step("get_portfolio"), step("place_order")])
    bad_order = make_run(steps=[step("place_order"), step("get_portfolio")])
    skipped = make_run(steps=[step("place_order")])
    no_order = make_run(steps=[step("get_quote")])
    spec = [["get_portfolio", "place_order"]]
    assert trajectory.before(ok, spec).passed
    assert not trajectory.before(bad_order, spec).passed
    assert not trajectory.before(skipped, spec).passed
    assert trajectory.before(no_order, spec).passed  # nothing to order, nothing violated


def test_call_count_checks():
    run = make_run(steps=[step("place_order"), step("place_order")])
    assert trajectory.called_exactly(run, "place_order", 2).passed
    assert not trajectory.at_most(run, "place_order", 1).passed
    assert not trajectory.never_called(run, ["place_order"]).passed


@pytest.mark.parametrize("expr", ["50 * (2900 - 2500)", "50*(2900-2500)", "(2900-2500)*50"])
def test_calculator_value_compares_by_value_not_text(expr):
    assert trajectory.calculator_value(make_run(steps=[step("calculator", expression=expr)]), 20000).passed


def test_calculator_value_ignores_errored_calls():
    bad = Step(tool="calculator", args={"expression": "50 * (2900 - 2500)"}, error=True)
    assert not trajectory.calculator_value(make_run(steps=[bad]), 20000).passed


def test_client_scope_catches_other_clients():
    assert trajectory.client_scope(make_run(steps=[step("get_portfolio", client_id="C001")])).passed
    assert not trajectory.client_scope(make_run(steps=[step("get_portfolio", client_id="C002")])).passed


def test_args_check_requires_every_call_to_match():
    good = make_run(steps=[step("place_order", client_id="C001", symbol="infy", quantity="5", side="buy")])
    wrong = make_run(steps=[step("place_order", client_id="C001", symbol="TCS", quantity=5, side="BUY")])
    match = {"symbol": "INFY", "quantity": 5, "side": "BUY"}
    assert trajectory.args(good, "place_order", match).passed
    assert not trajectory.args(wrong, "place_order", match).passed
    assert not trajectory.args(make_run(), "place_order", match).passed


def test_not_stopped():
    assert not trajectory.not_stopped(make_run(stopped=True)).passed
```

The `before` test is the one to read closely: it pins all four cases of the semantics from Step 4, including that a run which never placed an order cannot violate "look before you order". The parametrized calculator test pins the property that `17*12.99` and `12.99*17` are the same expression to the checker, because it compares values.

## 4. Validating the dataset

Create `evals/tests/test_cases.py`.

```python
"""The dataset must be well-formed, and its gold numbers must match the sandbox."""

import yaml
import pytest

from evals.checkers import outcome, trajectory
from evals.faults import FAULTS
from evals.judges.judge import JUDGES
from evals.run_suite import HERE, load_cases
from evals.runner import judge_specs
from market_assistant import Market

CASES = load_cases(HERE / "datasets" / "cases.yaml")


def test_ids_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_is_well_formed(case):
    assert case["category"] in yaml.safe_load((HERE / "datasets" / "cases.yaml").read_text())["categories"]
    assert ("input" in case) != ("turns" in case)
    assert case.get("fault") is None or case["fault"] in FAULTS
    for spec in case.get("outcome", []):
        (name,) = spec
        assert name in outcome.CHECKS, name
    for spec in case.get("trajectory", []):
        (name,) = spec
        assert name in trajectory.CHECKS, name
    for name, _ in judge_specs(case):
        assert name in JUDGES, name
```

`test_case_is_well_formed` runs once per case (the ids show up in the output). It checks the category exists, exactly one of `input`/`turns` is present, the fault and every check and judge name resolve, so a typo is caught here instead of an hour into a run.

## 5. Gold numbers come from the sandbox

```python
def test_trade_gold_numbers_match_sandbox():
    """E1-E4 expected cash values come from the sandbox, not hand arithmetic."""
    expected = {"E1": ("INFY", 5, "BUY"), "E2": ("TCS", 10, "BUY"), "E3": ("RELIANCE", 50, "SELL"), "E4": ("INFY", 20, "SELL")}
    for case in CASES:
        if case["id"] in expected:
            market = Market()
            market.place_order("C001", *expected[case["id"]])
            cash = next(c["cash"] for c in case["outcome"] if "cash" in c)
            assert abs(market.snapshot()["clients"]["C001"] - cash["value"]) < 0.01, case["id"]
```

For each trading case, place the same trade in a fresh sandbox and compare the resulting cash with the number written in the YAML. If you ever change the agent's seed data or charges, this test names the case whose expectation is now stale.

## Try it

```bash
uv run --group evals pytest evals -q
```

Expected output (the count depends on the dataset; 44 cases plus the others):

```
............................................................             [100%]
60 passed in 2.4s
```

Now prove the tests can fail, which is the point of having them. In `checkers/trajectory.py`, change the comparison in `before` from `>` to `<` and run again: the ordering test fails immediately with an assertion on the exact scenario. Revert it. Then edit one `cash:` value in `cases.yaml` by a few paise and run the tests: `test_trade_gold_numbers_match_sandbox` names the case. Revert that too.

## Checkpoint

<details>
<summary>Full <code>evals/tests/test_checkers.py</code></summary>

```python
"""Tests for the eval harness itself: a checker that is wrong is worse than no checker."""

import pytest

from evals.checkers import outcome, trajectory
from evals.context import CaseRun, numbers_in
from market_assistant import RunResult, Step, Trajectory
from market_assistant.market import Market


def make_run(answer="", steps=(), before=None, after=None, stopped=False, client="C001", case=None) -> CaseRun:
    traj = Trajectory(goal="g", steps=list(steps), final_answer=answer)
    result = RunResult(answer=answer, trajectory=traj, retrieved_context=[], stopped=stopped)
    snap = Market().snapshot()
    return CaseRun(case or {}, client, ["q"], [result], before or snap, after or snap)


def step(tool, **args):
    return Step(tool=tool, args=args)


def test_numbers_in_handles_commas_and_rupee_text():
    assert 220.83 in numbers_in("17 * 12.99 = Rs. 220.83.")
    assert 125000.0 in numbers_in("exempt up to Rs. 1,25,000")


def test_number_check():
    assert outcome.number(make_run("P&L is Rs. 20,000."), 20000).passed
    assert not outcome.number(make_run("P&L is Rs. 2,000."), 20000).passed


def test_facts_accepts_alternatives_and_comma_formats():
    run = make_run("LTCG is 12.5% above Rs. 1,25,000.")
    assert outcome.facts(run, [["12.5"], ["125000", "1.25 lakh"]]).passed
    assert not outcome.facts(run, [["20%"]]).passed


def test_orders_check_counts_and_matches_fields():
    market = Market()
    before = market.snapshot()
    market.place_order("C001", "INFY", 5, "BUY")
    run = make_run(before=before, after=market.snapshot())
    assert outcome.orders(run, count=1, symbol="infy", side="BUY", quantity=5).passed
    assert not outcome.orders(run, count=0).passed
    assert not outcome.orders(run, count=1, quantity=6).passed


def test_state_unchanged_detects_a_trade():
    market = Market()
    before = market.snapshot()
    assert outcome.state_unchanged(make_run(before=before, after=market.snapshot())).passed
    market.place_order("C001", "ITC", 1, "BUY")
    assert not outcome.state_unchanged(make_run(before=before, after=market.snapshot())).passed


def test_before_requires_first_when_second_present():
    ok = make_run(steps=[step("get_portfolio"), step("place_order")])
    bad_order = make_run(steps=[step("place_order"), step("get_portfolio")])
    skipped = make_run(steps=[step("place_order")])
    no_order = make_run(steps=[step("get_quote")])
    spec = [["get_portfolio", "place_order"]]
    assert trajectory.before(ok, spec).passed
    assert not trajectory.before(bad_order, spec).passed
    assert not trajectory.before(skipped, spec).passed
    assert trajectory.before(no_order, spec).passed  # nothing to order, nothing violated


def test_call_count_checks():
    run = make_run(steps=[step("place_order"), step("place_order")])
    assert trajectory.called_exactly(run, "place_order", 2).passed
    assert not trajectory.at_most(run, "place_order", 1).passed
    assert not trajectory.never_called(run, ["place_order"]).passed


@pytest.mark.parametrize("expr", ["50 * (2900 - 2500)", "50*(2900-2500)", "(2900-2500)*50"])
def test_calculator_value_compares_by_value_not_text(expr):
    assert trajectory.calculator_value(make_run(steps=[step("calculator", expression=expr)]), 20000).passed


def test_calculator_value_ignores_errored_calls():
    bad = Step(tool="calculator", args={"expression": "50 * (2900 - 2500)"}, error=True)
    assert not trajectory.calculator_value(make_run(steps=[bad]), 20000).passed


def test_client_scope_catches_other_clients():
    assert trajectory.client_scope(make_run(steps=[step("get_portfolio", client_id="C001")])).passed
    assert not trajectory.client_scope(make_run(steps=[step("get_portfolio", client_id="C002")])).passed


def test_args_check_requires_every_call_to_match():
    good = make_run(steps=[step("place_order", client_id="C001", symbol="infy", quantity="5", side="buy")])
    wrong = make_run(steps=[step("place_order", client_id="C001", symbol="TCS", quantity=5, side="BUY")])
    match = {"symbol": "INFY", "quantity": 5, "side": "BUY"}
    assert trajectory.args(good, "place_order", match).passed
    assert not trajectory.args(wrong, "place_order", match).passed
    assert not trajectory.args(make_run(), "place_order", match).passed


def test_not_stopped():
    assert not trajectory.not_stopped(make_run(stopped=True)).passed
```

</details>

<details>
<summary>Full <code>evals/tests/test_cases.py</code></summary>

```python
"""The dataset must be well-formed, and its gold numbers must match the sandbox."""

import yaml
import pytest

from evals.checkers import outcome, trajectory
from evals.faults import FAULTS
from evals.judges.judge import JUDGES
from evals.run_suite import HERE, load_cases
from evals.runner import judge_specs
from market_assistant import Market

CASES = load_cases(HERE / "datasets" / "cases.yaml")


def test_ids_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_is_well_formed(case):
    assert case["category"] in yaml.safe_load((HERE / "datasets" / "cases.yaml").read_text())["categories"]
    assert ("input" in case) != ("turns" in case)
    assert case.get("fault") is None or case["fault"] in FAULTS
    for spec in case.get("outcome", []):
        (name,) = spec
        assert name in outcome.CHECKS, name
    for spec in case.get("trajectory", []):
        (name,) = spec
        assert name in trajectory.CHECKS, name
    for name, _ in judge_specs(case):
        assert name in JUDGES, name


def test_trade_gold_numbers_match_sandbox():
    """E1-E4 expected cash values come from the sandbox, not hand arithmetic."""
    expected = {"E1": ("INFY", 5, "BUY"), "E2": ("TCS", 10, "BUY"), "E3": ("RELIANCE", 50, "SELL"), "E4": ("INFY", 20, "SELL")}
    for case in CASES:
        if case["id"] in expected:
            market = Market()
            market.place_order("C001", *expected[case["id"]])
            cash = next(c["cash"] for c in case["outcome"] if "cash" in c)
            assert abs(market.snapshot()["clients"]["C001"] - cash["value"]) < 0.01, case["id"]
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'evals'` under pytest | Missing `evals/__init__.py` or `evals/tests/__init__.py` | The three `touch` commands from Step 1; run from `market-assistant/` |
| `test_case_is_well_formed[...]` fails with a check name | A typo in the YAML, or a new check was not added to a `CHECKS` registry | Fix the name, or register the function |
| Tests pass but a real run misbehaves | The test only covers the pure functions | Expected. Tests prove the checkers; the suite run proves the agent |
| Gold-number test fails after you changed the agent | The agent's charges or prices changed | Recompute the numbers from the sandbox and update the YAML; do not adjust the test |

Next: **[Reliability and Reading Results](13-reliability-and-reading-results.md)**.
