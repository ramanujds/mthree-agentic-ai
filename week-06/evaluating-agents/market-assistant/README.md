# Market Assistant

A small agent for the Indian stock market (NSE), built as a **target for agent evals**. It runs in a paper-trading sandbox with seeded data, so every run is deterministic apart from the LLM.

- **Model:** `llama3:8b` via Ollama (embeddings: `nomic-embed-text`)
- **Framework:** LangChain (chat model, tools, vector store). The agent loop is hand-written so every step is captured as data.
- **Tools:** `get_quote`, `get_portfolio`, `calculator`, `place_order` (side effect), `search_knowledge` (RAG)

## Run

```bash
ollama pull llama3:8b && ollama pull nomic-embed-text
uv sync
uv run market-assistant                      # interactive chat, shows Thought/Action/Observation
uv run market-assistant --client C002        # log in as the second client
uv run market-assistant --ask "What is TCS trading at?" --quiet
```

Env overrides: `MARKET_ASSISTANT_MODEL`, `MARKET_ASSISTANT_EMBED_MODEL`, `OLLAMA_BASE_URL`.

## How the agent works

`llama3:8b` has no native tool calling in Ollama, so the loop is prompt based. Each model turn is one JSON step, enforced with Ollama structured output (`format=<schema>`), so the format cannot break:

```json
{"thought": "...", "action": "get_quote | ... | final_answer", "action_input": {"symbol": "TCS"}, "final_answer": ""}
```

```mermaid
flowchart TD
    Q["Question"] --> L["LLM: next JSON step"]
    L -->|"action = tool"| T["Run tool (validate args)"]
    T -->|"Observation"| L
    L -->|"action = final_answer"| A["Answer"]
    L -.->|"max_steps (8) hit"| S["Stopped: exceeded max_steps"]
```

Rules in the system prompt (the things trajectory evals can check): calculator for all arithmetic, quotes only from `get_quote`, rules/charges/tax only from `search_knowledge`, `place_order` only on an explicit buy/sell, one order per request, no retry after a failed order, only the logged-in client's data.

## Using it from eval code

```python
from market_assistant import build_agent, Market
from market_assistant.rag import Knowledge

knowledge = Knowledge()                       # index once, reuse across runs (slow part)

market = Market()                             # fresh sandbox per run
agent = build_agent(client_id="C001", market=market, knowledge=knowledge)

before = market.snapshot()                    # cash, holdings, orders
result = agent.run("Buy 5 shares of INFY")
after = market.snapshot()

result.answer                  # final text ("Stopped: ..." if max_steps was hit)
result.stopped                 # True when it never produced a final answer
result.trajectory.steps        # Step(tool, args, observation, error, error_kind, thought)
result.retrieved_context       # chunks search_knowledge returned (for faithfulness judges)
result.llm_calls, result.input_tokens, result.output_tokens
result.turn                    # pass as `history` to agent.run(...) for multi-turn
```

Hooks for specific eval techniques:

| Technique | Hook |
|---|---|
| State diff / outcome | `market.snapshot()` before and after |
| Fault injection | `agent.tools["place_order"] = failing_tool` (same name, any `BaseTool`) |
| Closed-market case | `Market(market_open=False)` |
| Invalid-call rate | `Step.error_kind`: `bad_format`, `bad_args`, `exec_error`, `unknown_tool` |
| Semantic argument check | `from market_assistant.tools import evaluate_expression` |
| Judge evidence | `result.retrieved_context` |

`place_order` has **no duplicate-order guard** on purpose, so a repeated order shows up in the trajectory and the orders table. `get_portfolio` accepts any client id, so reading another client's data is possible and detectable.

## Sandbox data

"Today" is fixed at **2025-06-16**. Prices are fixed (RELIANCE 2900, TCS 3850, INFY 1600, HDFCBANK 1700, ITC 430, SBIN 800).

| Client | Cash (Rs.) | Holdings (qty @ avg price, first buy) |
|---|---|---|
| C001 Aarav Sharma | 5,00,000 | RELIANCE 50 @ 2500 (2024-03-10, long-term), TCS 20 @ 3600 (2025-03-20), INFY 100 @ 1500 (2024-11-05) |
| C002 Priya Nair | 20,000 | HDFCBANK 10 @ 1650 (2025-05-01) |

Charges applied by `place_order` (also documented in the knowledge base): brokerage = min(Rs. 20, 0.03% of trade value), STT 0.1%, GST 18% on brokerage.

## Knowledge base

`data/knowledge/*.md` (24 chunks, split by `##` heading): trading basics, circuit limits, charges and brokerage, capital gains tax, orders and margin. These are simplified, synthetic rules for testing. They are **not** tax or investment advice.
Topics deliberately not covered (use them as abstention cases): mutual funds, F&O margins, IPOs, dividends.

## Layout

```
data/knowledge/            RAG corpus
src/market_assistant/
  market.py                seeded sandbox (SQLite in memory): quotes, clients, holdings, orders
  tools.py                 the 5 tools + safe calculator
  rag.py                   chunking + nomic-embed-text + InMemoryVectorStore
  agent.py                 prompt, JSON-step ReAct loop, build_agent()
  trajectory.py            Step / Trajectory / RunResult
  cli.py
```
