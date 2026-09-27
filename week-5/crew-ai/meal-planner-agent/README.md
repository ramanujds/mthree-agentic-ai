# meal-planner-agent (CrewAI)

A meal planning + budgeting + grocery shopping app built with **CrewAI** —
the CrewAI counterpart to
[../../langchain/meal-planner-agent](../../langchain/meal-planner-agent),
which solves the same problem with plain LangChain (LCEL). See
[../meal-planner-langchain-vs-crewai.md](../meal-planner-langchain-vs-crewai.md)
for a full comparison of the two implementations.

**Problem statement:** planning meals, budgeting, and building a grocery
list by hand means hours of browsing recipes, calculating quantities,
checking prices, and hoping it all fits your budget and diet. This app
automates that using a three-agent CrewAI crew.

- **Fully local**: the LLM runs through [Ollama](https://ollama.com) — no
  API key, nothing leaves your machine (same setup as
  [../../rag-with-langchain/simple-rag-example-chromadb](../../rag-with-langchain/simple-rag-example-chromadb)).
- **Structured outputs**: every task returns a validated Pydantic model
  (`MealPlan`, `ShoppingPlan`, `BudgetReport`) via `output_pydantic=...`.
- **CrewAI orchestration**: three agents, wired into one sequential
  `Crew`, with `context=[...]` passing each task's output into the next.

## Setup

1. Make sure [Ollama](https://ollama.com) is running and the model is pulled:

   ```bash
   ollama pull llama3:8b
   ```

2. Install deps and run:

   ```bash
   uv sync
   uv run main.py
   ```

Override `MEAL_BUDGET`, `MEAL_DIET`, `MEAL_COUNT`, `OLLAMA_LLM_MODEL`, or
`OLLAMA_BASE_URL` as environment variables, e.g.:

```bash
MEAL_BUDGET=60 MEAL_DIET=vegan MEAL_COUNT=3 uv run main.py
```

## What it does

Three agents in one sequential `Crew`:

1. **Meal Planner** — suggests N meals matching the diet and budget, each
   with ingredients (`output_pydantic=MealPlan`).
2. **Shopping Organizer** — equipped with a custom `price_lookup` tool
   (`tools.py`); gathers every ingredient from the meal plan (via
   `context`) and calls the tool once to price, categorize, and total
   everything (`output_pydantic=ShoppingPlan`).
3. **Budget Advisor** — checks the shopping plan's total against the
   budget (via `context`) and writes savings tips (`output_pydantic=BudgetReport`).

The three structured outputs are then rendered into `meal_plan_guide.md`.

### Why the pricing math isn't left to the LLM

`llama3:8b` isn't reliable at multi-item arithmetic, so `tools.py` computes
category subtotals and the grand total in plain Python — the agent's job
is just to gather ingredients and make one tool call, not to add numbers.
`main.py` also re-derives `BudgetReport.total_cost` /
`BudgetReport.within_budget` from that same Python-computed total after
`crew.kickoff()`, rather than trusting the model's copy of those numbers.

### Why there's an explicit example in the shopping task

`llama3:8b` doesn't support Ollama's native tool-calling API (confirmed
directly — Ollama returns `"does not support tools"` if you try
`.bind_tools()`-style calls against it). CrewAI copes with this itself: it
falls back to its own ReAct-style ("Thought/Action/Action Input") text
prompting when native function-calling fails, so tool use still works —
but an 8B model isn't reliable at inferring a new tool's JSON argument
shape unsolicited, so the task description spells out an example
`Action Input` to copy.

## Files

- `models.py` — shared Pydantic schema for all three tasks.
- `price_catalog.py` — local, offline price/category lookup.
- `tools.py` — the `price_lookup` CrewAI tool.
- `report.py` — renders the final Markdown guide.
- `main.py` — agents, tasks, crew, and entry point.
