# Step 2 — Capturing a Run

> [Back to index](README.md) · Previous: [Setup and Agent Contract](02-setup-and-agent-contract.md) · Next: [Outcome Checks](04-outcome-checks.md)

## Goal

Build `context.py`: the `CaseRun` record that holds everything about one case execution (answer, tool calls, sandbox before and after), and the `CheckResult` every checker returns.

## Why this matters

Every checker in this harness is a function from a `CaseRun` to a `CheckResult`. That single decision does a lot of work:

- **Checkers never run the agent.** They read a recording. So they are fast, deterministic, and testable with a hand-built record, no model required (Step 11).
- **Checkers cannot interfere with each other.** Each reads the same recording and returns a verdict.
- **State is compared, not inferred.** The record keeps the sandbox snapshot from before the run and after it. "Did the agent place an order?" becomes "are there more rows in the orders table than before?", which is a fact, not a guess from the agent's wording.

`CheckResult` carries a `detail` string as well as `passed`. A check that only says "failed" is nearly useless; one that says `numbers in answer: [5.0, 1600.0, 491989.17]` tells you what the agent actually said. Most debugging time in an eval suite is spent reading these details, so write them as if you will be the one reading them at 6pm.

`CaseRun` also merges multi-turn cases: `steps` concatenates the tool calls from every turn, and `answer` is the last turn's. Checkers do not need to know whether a case had one turn or three.

## 1. The verdict type

Start `evals/context.py` with the module docstring, imports and the verdict type. `passed` drives pass/fail; `detail` is for humans.

```python
"""Shared types: what a checker or judge sees after one case has been run."""

import re
from dataclasses import dataclass, field

from market_assistant import RunResult, Step


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
```

## 2. The run record

`CaseRun` is a plain dataclass. The agent produces one `RunResult` per turn; the runner (Step 7) adds the sandbox snapshots and timing.

```python
@dataclass
class CaseRun:
    """One execution of one case (all turns), plus the sandbox state before and after."""

    case: dict
    client_id: str
    turns: list[str]
    results: list[RunResult]
    before: dict  # Market.snapshot()
    after: dict
    latency_s: float = 0.0
```

## 3. Convenience views

Properties so that checkers read naturally (`ctx.tools`, `ctx.stopped`) instead of digging through `results[-1].trajectory.steps` everywhere.

```python
    @property
    def answer(self) -> str:
        return self.results[-1].answer

    @property
    def steps(self) -> list[Step]:
        return [s for r in self.results for s in r.trajectory.steps]

    @property
    def tools(self) -> list[str]:
        return [s.tool for s in self.steps]

    @property
    def stopped(self) -> bool:
        return any(r.stopped for r in self.results)
```

`stopped` is true if *any* turn hit the agent's step limit without producing a final answer. Treating that as a failure everywhere is one of the universal checks in Step 4.

## 4. The state diff

```python
    @property
    def new_orders(self) -> list[dict]:
        return self.after["orders"][len(self.before["orders"]) :]

    @property
    def llm_calls(self) -> int:
        return sum(r.llm_calls for r in self.results)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.results)

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.results)
```

The orders table only ever grows, and `snapshot()["orders"]` is ordered. So the orders the agent created are exactly the rows past the old length. This one property is what lets the outcome checks say "exactly one new order, for 5 INFY" without any fragile parsing of the agent's wording. The token properties feed the cost columns in the report.

## 5. Text helpers

```python
def numbers_in(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def normalise(text: str) -> str:
    """Lowercase and drop thousands separators so '1,25,000' matches '125000'."""
    return re.sub(r"\s+", " ", text.lower().replace(",", "")).strip()
```

`numbers_in` pulls every number out of the answer, dropping commas first so that `Rs. 1,25,000` and `Rs. 125000` are the same. `normalise` lowercases and drops commas so that a fact like `1,25,000` can be matched whichever way the agent wrote it. Both are intentionally crude: they feed checks that are cheap and objective, and the cases where wording really matters go to the judge in Step 8.

## Try it

First a throwaway helper that produces one real `CaseRun` you can poke at for the next few steps. Create `scratch.py` in the **`market-assistant/` folder** (not inside `evals/`) and delete it when you finish Step 7:

```python
"""Throwaway helper for the walkthrough: one real agent run wrapped as a CaseRun. Delete it at the end."""

from evals.context import CaseRun
from market_assistant import Market, build_agent
from market_assistant.rag import Knowledge

QUESTION = "Buy 5 shares of INFY"

market = Market()
agent = build_agent(client_id="C001", market=market, knowledge=Knowledge())
before = market.snapshot()
result = agent.run(QUESTION)
run = CaseRun({}, "C001", [QUESTION], [result], before, market.snapshot())

if __name__ == "__main__":
    print("answer :", run.answer)
    print("tools  :", run.tools)
    print("orders :", [(o["symbol"], o["side"], o["quantity"]) for o in run.new_orders])
    print("llm calls:", run.llm_calls, " tokens:", run.input_tokens + run.output_tokens)
```

The first two arguments to `CaseRun` are the case dict (empty for now) and the logged-in client. Run it:

```bash
uv run python scratch.py
```

Expected output (the wording and token count vary a little between runs):

```
answer : You have bought 5 shares of INFY at Rs. 1600.00. Your new cash balance is Rs. 491,989.17.
tools  : ['get_portfolio', 'get_quote', 'place_order']
orders : [('INFY', 'BUY', 5)]
llm calls: 4  tokens: 4960
```

Notice `orders` comes from the snapshot diff, not from the answer text. If the agent had *claimed* to buy but failed, `tools` might still end in `place_order`, but `orders` would be empty.

## Checkpoint

<details>
<summary>Full <code>evals/context.py</code></summary>

```python
"""Shared types: what a checker or judge sees after one case has been run."""

import re
from dataclasses import dataclass, field

from market_assistant import RunResult, Step


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseRun:
    """One execution of one case (all turns), plus the sandbox state before and after."""

    case: dict
    client_id: str
    turns: list[str]
    results: list[RunResult]
    before: dict  # Market.snapshot()
    after: dict
    latency_s: float = 0.0

    @property
    def answer(self) -> str:
        return self.results[-1].answer

    @property
    def steps(self) -> list[Step]:
        return [s for r in self.results for s in r.trajectory.steps]

    @property
    def tools(self) -> list[str]:
        return [s.tool for s in self.steps]

    @property
    def stopped(self) -> bool:
        return any(r.stopped for r in self.results)

    @property
    def new_orders(self) -> list[dict]:
        return self.after["orders"][len(self.before["orders"]) :]

    @property
    def llm_calls(self) -> int:
        return sum(r.llm_calls for r in self.results)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.results)

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.results)


def numbers_in(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def normalise(text: str) -> str:
    """Lowercase and drop thousands separators so '1,25,000' matches '125000'."""
    return re.sub(r"\s+", " ", text.lower().replace(",", "")).strip()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `new_orders` is always empty | Took the `before` snapshot after running the agent | Snapshot first, run second, snapshot again |
| `new_orders` includes orders from the previous run | Reused one `Market` across runs | A fresh `Market()` per run (the runner does this in Step 7) |
| `ImportError: cannot import name 'RunResult'` | Importing from a submodule that does not export it | `from market_assistant import RunResult, Step` as the contract in Step 1 lists |
| `scratch.py` cannot import `evals` | Created it inside `evals/` | Put it in `market-assistant/` so `evals` is on the import path |

Next: **[Outcome Checks](04-outcome-checks.md)**.
