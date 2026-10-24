# Meridian Support Assistant - Capstone Starter Kit (zero cost)

Everything here runs **offline on a laptop CPU with free, open-source software**. No API keys, no cloud accounts, no paid services.
You build ONE integrated application in `assignments/capstone/`. **Open `START_HERE.md` first** (step-by-step path, how to get help, common problems), then read the Capstone Brief.

## Setup (10 minutes)
    python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python -m autograde.run --capstone --root .               # everything fails until you implement it - that is expected (add -v to see each failing check)

## Folders
| Folder | What |
|---|---|
| `assignments/capstone/` | **your work goes here**: `app.py` (the integrated app), module stubs with contracts in their docstrings, `stretch/` (optional), `templates/` |
| `data/` | synthetic Meridian Bank corpus (`data/corpus/`), accounts, public eval questions, red-team payloads, three stakeholder interviews. All fictional. |
| `harness/` | the free offline toolbox: `RuleLLM`, `HashingEmbedder` + BM25, fake back-office systems, fault injection (`GAMEDAY_FAULT`) |
| `autograde/` | the checks the trainer runs on your submission - run them yourself first |
| `examples/` | two tiny runnable examples: Pydantic-AI and LlamaIndex Workflows without any LLM key |

## Checks
    python -m autograde.run --capstone --root . -v      # automated score /40, evidence gate, stretch bonus, zero-cost scan
    cd assignments/capstone && python app.py --demo     # your end-to-end demo (must exit 0 offline)
    GAMEDAY_FAULT=tool_outage python app.py --demo      # must still exit 0 and print "degraded" or "fallback"

## Windows and other notes
- Windows: activate the environment with `.venv\Scripts\activate`. If you ever see strange characters or decoding errors, set `PYTHONUTF8=1` first, and open files in your own code with `encoding="utf-8"`.
- Tested with Python 3.13; 3.11 or newer is expected to work. Dependency versions are bounded in `requirements.txt`.
- Tests: put them in `assignments/capstone/tests/` and run `python -m pytest assignments/capstone/tests`. A `conftest.py` already makes imports work.
- Templates for every document, a CI workflow, a sample evaluation dataset and starter tests are in `assignments/capstone/templates/`.

## The zero-cost rules (non-negotiable)
1. **No paid or keyed services**: no OpenAI / Azure OpenAI / Anthropic / Cohere / Pinecone / cloud vector DBs, no free-tier APIs that need a key. The scanner fails a submission that imports a hosted-model SDK or reads such a key from the environment.
2. **No secrets in your repo** (`.env` with keys, hard-coded tokens).
3. **Models**: use `harness.llm.RuleLLM` / `ScriptedLLM` / `MockExtractionLLM`. A *local* Ollama model is an optional extra; your submission must still pass with the harness models only.
4. **Data**: only the synthetic data in `data/`. Never paste real customer or employer data into anything.
5. Anything optional that you add must be free, open source and runnable locally.

## Submitting
Zip `assignments/capstone/` together with `autograde_output.txt` (the saved output of `python -m autograde.run --capstone --root .`), without `__pycache__`, `.venv` or any `.env` file, and send it to your trainer. `START_HERE.md` step 12 has the exact commands.
The trainer re-runs the checks with **hidden questions, attack samples and scenarios** (so tuning to the public examples or hard-coding answers does not pay), reads your documents, and holds a 30-minute defence (demo, viva, live change, game day).
