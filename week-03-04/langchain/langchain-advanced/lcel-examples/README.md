# LCEL Examples

Five minimal, standalone scripts illustrating the core patterns from [../langchain-LCEL.md](../langchain-LCEL.md) and [../LCEL-cheatsheet.md](../LCEL-cheatsheet.md) — the pipe operator, type coercion, data manipulation, and execution modes.

| Script | Demonstrates |
| --- | --- |
| [01_pipe_sequence.py](01_pipe_sequence.py) | The pipe operator building a `RunnableSequence`: `prompt \| llm \| parser` |
| [02_runnable_parallel.py](02_runnable_parallel.py) | A `dict` auto-coercing into `RunnableParallel` — concurrent branches over the same input |
| [03_runnable_lambda.py](03_runnable_lambda.py) | A plain function auto-coercing into `RunnableLambda` |
| [04_passthrough_assign.py](04_passthrough_assign.py) | `RunnablePassthrough.assign()` to enrich input with retrieved context (mini RAG shape) |
| [05_batch_and_stream.py](05_batch_and_stream.py) | The same chain run via `invoke()`, `batch()`, and `stream()` |

## Setup

1. Start a local model via Docker Model Runner — see [../../code/00-local-model-setup/README.md](../../code/00-local-model-setup/README.md). (Or point `ChatOpenAI` in any script at a hosted provider instead — just change `base_url`/`api_key`.)
2. Install dependencies:

   ```bash
   cd langchain/langchain-advanced/lcel-examples
   uv sync
   ```

## Run

```bash
uv run 01_pipe_sequence.py
uv run 02_runnable_parallel.py
uv run 03_runnable_lambda.py
uv run 04_passthrough_assign.py
uv run 05_batch_and_stream.py
```

## Env vars

All scripts read the same variables as the `code/` examples:

```bash
export DMR_MODEL=docker.io/ai/gemma4:E4B
export DMR_BASE_URL=http://localhost:12434/v1
```
