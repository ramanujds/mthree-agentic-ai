# Step 1 — Setup and Agent Contract

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Capturing a Run](03-capturing-a-run.md)

## Goal

Create the `evals/` skeleton with its own dependency group, and write down exactly which parts of the agent the eval code is allowed to depend on.

## Why this matters

Two decisions made here shape everything after.

**Evals get their own dependency group.** `pyyaml` and `pytest` are needed to run evals, not to run the agent. Putting them in a `uv` dependency group (`--group evals`) keeps the agent's runtime dependencies clean, so anyone who only wants the assistant never installs test tooling. The cost is one extra flag on every command. Forgetting it is the most common first error, so it is in the mistakes table below.

**The agent is a black box with a small, explicit contract.** Evals that reach into agent internals break every time the agent is refactored. These evals use only the handful of public pieces in the table below. Notice what is *not* on the list: no prompt text, no loop internals, no tool implementation. If you can evaluate an agent through a narrow interface like this, you can swap in a different agent (a different model, a different framework) and keep the same suite. That is how you compare variants later.

## 1. Check the agent works

You need the agent's two Ollama models and a working agent before touching evals. From the `market-assistant/` folder:

```bash
ollama list                      # expect llama3:8b and nomic-embed-text
uv run market-assistant --ask "What is TCS trading at?" --quiet
```

The agent should answer with a price of 3850. If it does not, fix that first using [../README.md](../README.md); nothing in this walkthrough can compensate for a broken agent.

## 2. Add the eval dependency group

```bash
uv add --group evals pyyaml pytest
```

`uv` writes a `[dependency-groups]` table into `pyproject.toml`. From now on, every command that runs eval code uses `uv run --group evals ...`.

## 3. Create the skeleton

```bash
mkdir -p evals/checkers evals/judges evals/datasets evals/tests
touch evals/__init__.py evals/tests/__init__.py evals/judges/__init__.py
```

`evals/checkers/__init__.py` is written for real in Step 5, so it is not created here. The three empty `__init__.py` files make `evals` an importable package, which is what lets `python -m evals.run_suite` and `from evals.context import CaseRun` work.

## 4. Keep run output out of version control

Append to the project's `.gitignore`:

```
# eval outputs
evals/results/
```

Every suite run writes a JSONL file there, and the judge cache lives there too (Step 8). They are large, regenerable and machine-specific.

## 5. The contract: what evals may use from the agent

| Piece | Used for | Where it appears |
| --- | --- | --- |
| `build_agent(client_id, market, knowledge, model, temperature, seed)` | Build a fresh agent per run, with a chosen seed and temperature | `runner.py` |
| `agent.run(goal, history)` | Run one turn. Returns a `RunResult` | `runner.py` |
| `RunResult`: `answer`, `trajectory.steps`, `stopped`, `turn`, `llm_calls`, `input_tokens`, `output_tokens` | Everything the checkers read | `context.py` |
| `Step`: `tool`, `args`, `observation`, `error`, `error_kind` | One tool call | trajectory checks, judges |
| `agent.tools` (a dict of tool name to tool) | Swap a tool for a failing one | `faults.py` |
| `Market(market_open=...)` and `market.snapshot()` | A fresh sandbox, and its full state as plain data | `runner.py`, outcome checks |
| `Knowledge()` | The RAG index. Slow to build, so built once per suite | `run_suite.py` |
| `market_assistant.tools.evaluate_expression` | Evaluate a calculator expression by value | trajectory checks |

`RunResult.turn` is the question plus the agent's final reply as messages. Passing it back as `history` is how multi-turn cases carry memory forward.

## 6. The seeded world the gold values come from

The sandbox is fixed, so every expected value in the dataset can be computed rather than guessed. "Today" is 2025-06-16.

| Client | Cash (Rs.) | Holdings (quantity at average buy price, first buy date) |
| --- | --- | --- |
| C001 | 5,00,000 | RELIANCE 50 at 2500 (2024-03-10), TCS 20 at 3600 (2025-03-20), INFY 100 at 1500 (2024-11-05) |
| C002 | 20,000 | HDFCBANK 10 at 1650 (2025-05-01) |

Prices: RELIANCE 2900, TCS 3850, INFY 1600, HDFCBANK 1700, ITC 430, SBIN 800.

## Try it

Confirm the eval group is installed and the contract imports resolve:

```bash
uv run --group evals python -c "
import yaml, pytest
from market_assistant import build_agent, Market, RunResult, Step, Trajectory
from market_assistant.rag import Knowledge
from market_assistant.tools import evaluate_expression
m = Market()
print('cash C001:', m.snapshot()['clients']['C001'])
print('17 * 12.99 =', evaluate_expression('17 * 12.99'))
"
```

Expected output:

```
cash C001: 500000.0
17 * 12.99 = 220.83
```

## Checkpoint

This step changes one project file (the rest is empty files and directories). The `[dependency-groups]` table at the bottom is what `uv add --group evals` produced; the rest belongs to the agent.

<details>
<summary>Full <code>pyproject.toml</code></summary>

```toml
[project]
name = "market-assistant"
version = "0.1.0"
description = "Indian stock market paper-trading assistant: a small ReAct agent (llama3:8b via Ollama) with tools and RAG, built as a target for agent evals"
readme = "README.md"
authors = [
    { name = "ramanujds", email = "ramanujds9@gmail.com" }
]
requires-python = ">=3.12"
dependencies = [
    "langchain-core>=0.3",
    "langchain-ollama>=0.3",
    "numpy>=2.5.3",
]

[project.scripts]
market-assistant = "market_assistant.cli:main"

[build-system]
requires = ["uv_build>=0.9.7,<0.10.0"]
build-backend = "uv_build"

[dependency-groups]
evals = [
    "pytest>=9.1.1",
    "pyyaml>=6.0.3",
]
```

</details>

Your tree under `evals/` is now only empty directories and three empty `__init__.py` files.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'yaml'` (later steps) | Ran `uv run` without the eval group | Use `uv run --group evals ...` for every eval command |
| `ModuleNotFoundError: No module named 'evals'` | Missing `evals/__init__.py`, or running from the wrong folder | `touch evals/__init__.py` and run from `market-assistant/` |
| `ollama` connection errors | Ollama not running, or models not pulled | Start Ollama and `ollama pull llama3:8b nomic-embed-text` |
| Agent answers but prices are different | Edited the agent's seed data | Restore the seeded prices; the gold values in Step 5 assume them |

Next: **[Capturing a Run](03-capturing-a-run.md)**.
