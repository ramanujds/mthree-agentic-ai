# Capstone Guides: Index

These short guides explain the kit in plain language. They do not replace the [Capstone Brief](../Agentic_AI_Capstone_Brief_V1.0.docx), which has the full requirements and scoring. They just tell you **what each file is, where to write your code, and which commands to run**.

## What you are building (30-second version)

One offline Python app, the **Meridian Support Assistant** for a fictional bank. You call `app.handle("some question", role)` and it must:

1. check the caller's **role** is allowed (least privilege),
2. **retrieve** policy text and treat it as data only (no prompt injection),
3. **answer** using safe tools, cite sources, and never leak personal data (PII),
4. write an **audit entry** and **trace spans**,
5. **survive faults** (say "degraded" and hand over to a human instead of crashing).

You then measure it, break it on purpose (game day), document it, and defend it in person.

## Read in this order

| # | Guide | Read it when |
|---|---|---|
| 1 | [01_SETUP.md](01_SETUP.md) | Day 1. Install Python packages and check the kit works. |
| 2 | [02_RUN_AND_TEST.md](02_RUN_AND_TEST.md) | Always open. Every command: checker, demo, tests, faults, eval gate. |
| 3 | [03_FOLDER_AND_FILE_MAP.md](03_FOLDER_AND_FILE_MAP.md) | Day 1. What every folder and file is for, and which ones you must not touch. |
| 4 | [04_WHERE_TO_WRITE_CODE.md](04_WHERE_TO_WRITE_CODE.md) | Days 2-4. The main guide: requirement, then file, then function, in build order. |
| 5 | [05_DOCUMENTS_AND_DELIVERABLES.md](05_DOCUMENTS_AND_DELIVERABLES.md) | Days 4-5. Every document and artefact you must produce, where it goes, what the checker looks for. |
| 6 | [06_TROUBLESHOOTING_AND_SUBMIT.md](06_TROUBLESHOOTING_AND_SUBMIT.md) | When stuck, and before you submit. |

There is also the existing one-page map, [CAPSTONE_PARTICIPANT_GUIDE.md](../CAPSTONE_PARTICIPANT_GUIDE.md), and the kit's own [START_HERE.md](../kit/START_HERE.md) (12-step path).

## The three rules that cost the most points

1. **All your code goes in `kit/assignments/capstone/`.** Never edit `kit/harness/` or `kit/autograde/`.
2. **No paid or keyed services** (OpenAI, Anthropic, Cohere, Pinecone...). Use the offline models in `harness/llm.py`. The zero-cost scan fails the submission otherwise.
3. **Do not memorise the public examples.** The trainer re-runs everything with hidden questions and attacks. Write general code.

## One-screen picture

```
 request + role
      |
      v
 app.handle()  (app.py)
   |-- authorize(role, tool) ........ a7_guard.py
   |-- agent.handle() ............... a4_agent.py
   |      |-- tools ................. a4_tools.py  (lookup / fee / escalate / search_policy)
   |      |-- retrieve .............. a2_rag.py    (or harness retriever)
   |      |-- sanitize + redact ..... a7_guard.py
   |-- resilience (retry/breaker) ... a7_resilience.py
   |-- audit entry .................. a7_audit.py
   |-- trace spans .................. a6_evals.py (Tracer)
      |
      v
 AgentResult (answer, sources, needs_human, confidence, ...)
```
