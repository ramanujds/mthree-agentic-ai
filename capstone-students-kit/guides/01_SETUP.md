# 01. Setup

About 10 minutes. You need internet only for `pip install`; after that everything runs offline.

## What you need

- Python **3.11 or newer** (the kit was tested on 3.13; a 3.15 install also worked when this guide was written). Check: `python3 --version`.
- A terminal and any editor (VS Code is fine).
- No GPU, no API key, no cloud account.

## Step 1. Open a terminal in the `kit` folder

The `kit` folder is the one that contains `assignments`, `autograde`, `data`, `harness` and `requirements.txt`.

```bash
cd capstone-students-kit/kit
ls          # you should see: assignments  autograde  data  examples  harness  requirements.txt
```

Almost every command in these guides is run from here ("the kit folder"). The exceptions say so.

## Step 2. Create and activate a virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell or cmd):

```bat
python -m venv .venv
.venv\Scripts\activate
```

Your prompt now starts with `(.venv)`. You must re-activate it in every new terminal.

## Step 3. Install the packages

```bash
pip install -r requirements.txt
```

This installs: `pydantic` (data models), `networkx` (stretch graph), `pytest` (tests), `llama-index-core` and `pydantic-ai-slim` (optional agent frameworks, used offline in `examples/`). All are free.

## Step 4. Check the kit works

```bash
python -m autograde.run --capstone --root .
```

Expected at the start:

```
AUTOMATED SCORE: 0.0/40
EVIDENCE GATE: FAIL (0.0/29, needs >= 23); STRETCH BONUS: 0.0/5
ZERO-COST SCAN: PASS
```

A score of 0 is **correct**: the stubs are not implemented yet. The thing to confirm is that the command runs without a Python error and the scan says PASS.

## Windows notes

- If you see strange characters or a `UnicodeDecodeError`, set `PYTHONUTF8=1` first (PowerShell: `$env:PYTHONUTF8="1"`) and open your own files with `encoding="utf-8"`.
- Setting an environment variable for one run: PowerShell `$env:GAMEDAY_FAULT="tool_outage"`; cmd `set GAMEDAY_FAULT=tool_outage`.

## Optional extras (skip unless you want them)

- `arize-phoenix`: a local trace UI. Free, not required.
- Ollama (a local model server from ollama.com): `harness/llm.py` has an `OllamaLLM` wrapper. Your submission must still pass using only the harness models (`RuleLLM`, `ScriptedLLM`).

## Create your working folders

You will need these next to `app.py` later (the checker looks for them). You can create them now or when you reach them:

```bash
cd assignments/capstone
mkdir -p docs reports traces audit gameday demo tests .github/workflows
cd ../..
```

Next: [02_RUN_AND_TEST.md](02_RUN_AND_TEST.md).
