# LangChain Tool Examples

Two minimal, standalone scripts matching [../langchain-overview.md](../langchain-overview.md)'s **Tools** section — same tool-calling flow (bind → model decides → execute → feed result back), first with a tool LangChain ships for you, then with one you write yourself.

| Script | Demonstrates |
| --- | --- |
| [01_builtin_tool.py](01_builtin_tool.py) | Using a **built-in tool** (`WikipediaQueryRun`) |
| [02_custom_tool.py](02_custom_tool.py) | Creating a **custom tool** with the `@tool` decorator |

## Setup

1. Start a local model via Docker Model Runner — see [../../code/00-local-model-setup/README.md](../../code/00-local-model-setup/README.md). (Or point `ChatOpenAI` in either script at a hosted provider instead — just change `base_url`/`api_key`.)
2. Install dependencies:

   ```bash
   cd langchain/tool-examples
   uv sync
   ```

## Run

```bash
uv run 01_builtin_tool.py
uv run 02_custom_tool.py
```

Both scripts print the tool's schema (name, description, args) before invoking the model, then show whether the model chose to call the tool and what it answered.

## Env vars

Both scripts read the same variables as the `code/` examples:

```bash
export DMR_MODEL=docker.io/ai/gemma4:E4B
export DMR_BASE_URL=http://localhost:12434/v1
```
