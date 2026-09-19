# Agent With Tool — Calculator Examples

Runnable companion code for [../agent-with-tool.md](../agent-with-tool.md) and
[../langchain-advanced/interactive-agents.md](../langchain-advanced/interactive-agents.md):
manual tool-calling agents with `add`, `subtract`, `multiply`, and `divide`
tools that handle multi-step tool chains (`(3 + 2) * 4`) and multi-turn
memory ("now divide that by 5").

| Script | Demonstrates |
| --- | --- |
| [calculator_agent.py](calculator_agent.py) | Full manual tool-calling loop as a plain function: bind tools → dispatch by name → feed `ToolMessage` results back → repeat until plain text |
| [tool_calling_agent.py](tool_calling_agent.py) | The same loop encapsulated in a `ToolCallingAgent` class that owns its own `chat_history`, plus step-by-step extraction of `tool_calls` name/args/id |

## Setup

1. Start a local Gemma model via Docker Model Runner — see [../../code/00-local-model-setup/README.md](../../code/00-local-model-setup/README.md). (Or point `ChatOpenAI` in the script at a hosted provider instead — just change `base_url`/`api_key`.)
2. Install dependencies:

   ```bash
   cd langchain/agent-with-tool-example
   uv sync
   ```

## Run

```bash
uv run calculator_agent.py
uv run tool_calling_agent.py
```

Expected output for `calculator_agent.py` (tool calls printed as they
happen, then the model's final natural-language answer for each turn):

```text
User: What is 3 plus 2?
  -> called add({'a': 3, 'b': 2}) = 5.0
Agent: 3 plus 2 is 5.

User: What is (3 + 2) times 4?
  -> called add({'a': 3, 'b': 2}) = 5.0
  -> called multiply({'a': 5, 'b': 4}) = 20.0
Agent: (3 + 2) times 4 is 20.

User: Now divide that by 5.
  -> called divide({'a': 20, 'b': 5}) = 4.0
Agent: 20 divided by 5 is 4.
```

Expected output for `tool_calling_agent.py` (note the deliberately
imprecise second query, and the third query relying on chat-history memory):

```text
User: What is 3 plus 2?
  -> called add({'a': 3, 'b': 2}) = 5.0
Agent: 3 plus 2 is 5.

User: 1 minus 2
  -> called subtract({'a': 1, 'b': 2}) = -1.0
Agent: 1 minus 2 is -1.

User: and now multiply that by 10
  -> called multiply({'a': -1, 'b': 10}) = -10.0
Agent: Multiplying -1 by 10 gives -10.
```

## Env vars

```bash
export DMR_MODEL=docker.io/ai/gemma4:E4B
export DMR_BASE_URL=http://localhost:12434/v1
```
