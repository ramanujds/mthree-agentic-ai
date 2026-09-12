# The LangChain Ecosystem

LangChain has grown from a single Python library into a family of separate but
interoperable projects. Each one solves a different part of the "build → debug →
deploy → operate" lifecycle for LLM applications.

```
Build            Orchestrate           Observe/Evaluate        Deploy/Run
────────────     ──────────────        ─────────────────       ─────────────
LangChain   ───▶  LangGraph      ───▶   LangSmith        ───▶   LangGraph Platform
(chains,          (stateful,             (tracing, eval,         (managed hosting,
 tools,            multi-agent            datasets,               persistence,
 retrievers)       graphs)                monitoring)             human-in-the-loop)
```

---

## 1. LangChain (core framework)

The original library: a set of abstractions for prompts, chat models, output
parsers, retrievers, tools, and "chains" that pipe them together (via LCEL —
LangChain Expression Language, the `|` pipe operator). Split into
`langchain-core`, `langchain`, `langchain-community`, and per-provider packages
like `langchain-openai`, `langchain-anthropic`.

**Use cases**
- RAG (retrieval-augmented generation) pipelines over documents/vector stores
- Simple tool-calling agents
- Prompt templating and structured output parsing
- Gluing together a model + retriever + vector DB + memory quickly

**Pros**
- Huge integration surface — hundreds of vector stores, document loaders, model
  providers, tools already wrapped for you
- LCEL gives composable, swappable pipelines with built-in streaming, batching,
  and async support
- Large community, lots of tutorials/examples, fast to prototype with
- Provider-agnostic: swap OpenAI for Anthropic/Bedrock/local models with
  minimal code changes

**Limitations**
- Abstraction layers can obscure what's actually being sent to the model,
  making debugging painful without LangSmith
- API has churned a lot across versions (0.0.x → 0.1 → 0.2 → 0.3); older
  tutorials/code break easily
- "Framework tax" — for a single well-defined LLM call, raw SDK calls are
  often simpler and more transparent than a LangChain chain
- Not itself built for complex multi-step/multi-agent control flow (loops,
  branching, retries) — that's what LangGraph is for

---

## 2. LangGraph

A lower-level orchestration library for building agents and multi-step
workflows as an explicit **graph** (nodes = functions/LLM calls, edges =
control flow, plus persisted state). Designed to replace LangChain's older
`AgentExecutor` for anything beyond trivial agent loops.

**Use cases**
- Multi-agent systems (supervisor/worker patterns, agent handoffs)
- Long-running agents needing durable state, checkpointing, or "time travel"
  debugging
- Human-in-the-loop workflows (pause for approval, resume later)
- Cyclical workflows — retries, self-correction loops, plan-execute-replan

**Pros**
- Explicit control over branching/looping instead of relying on an LLM to
  "decide" flow — more predictable and testable
- Built-in persistence/checkpointing, so agents can pause and resume (useful
  for human approval steps or long-running tasks)
- Works standalone — doesn't require the rest of LangChain, can wrap raw
  model calls
- First-class support in LangSmith and LangGraph Platform for tracing/deploy

**Limitations**
- Steeper learning curve than a simple chain — you're explicitly designing a
  state machine
- More boilerplate for simple use cases (overkill if you just need one
  tool-calling loop)
- Still a fairly young API; patterns/best practices are still settling

---

## 3. LangSmith

A hosted (or self-hosted) observability and evaluation platform: traces every
LLM call, chain, and agent step; supports dataset-based evaluation, prompt
versioning/playground, and production monitoring (latency, cost, feedback
scores).

**Use cases**
- Debugging why an agent/chain produced a bad output (full trace of
  inputs/outputs at every step)
- Regression testing prompts/chains against a golden dataset before shipping
- Production monitoring — cost, latency, error rates, user feedback
- A/B testing prompts

**Pros**
- Dramatically shortens debugging time vs. reading raw logs — visual trace
  tree of nested chain/agent calls
- Works with LangChain/LangGraph out of the box (just set env vars), and also
  supports non-LangChain apps via the SDK
- Good eval tooling (LLM-as-judge, custom evaluators, dataset management)

**Limitations**
- SaaS by default — sends trace data to LangChain's servers, which is a
  concern for sensitive/regulated data (self-hosted option exists but is an
  enterprise feature, extra ops burden)
- Adds a paid dependency for serious usage at scale (pricing by traces)
- Most value is unlocked when you're already in the LangChain/LangGraph
  ecosystem; wiring it into a fully custom stack takes more manual instrumentation

---

## 4. LangGraph Platform (formerly LangServe / LangGraph Cloud)

Deployment and hosting layer for LangGraph agents — turns a graph into a
managed API with built-in persistence, streaming, horizontal scaling, and a
UI (LangGraph Studio) for visually inspecting/debugging running graphs.
**LangServe** (the older, simpler "deploy any LangChain Runnable as a REST
API" tool) is now in maintenance mode, effectively superseded by this.

**Use cases**
- Taking a LangGraph agent from prototype to a production HTTP service
- Needing durable execution across server restarts (long-running/human-in-
  the-loop agents)
- Visual debugging of live agent runs via LangGraph Studio

**Pros**
- Handles the undifferentiated heavy lifting: persistence, streaming,
  retries, horizontal scaling
- Tight integration with LangGraph's checkpointing model
- Studio UI is genuinely useful for inspecting agent state step-by-step

**Limitations**
- Managed offering is another hosted dependency/cost; self-hosting is
  possible but adds infra work
- Locks you further into the LangGraph state/graph model — harder to migrate
  away later
- Less mature than established deployment options (plain FastAPI + your own
  infra, AWS Bedrock Agents, etc.)

---

## 5. LangChain Hub / Templates

A registry for sharing and versioning prompts (and formerly, ready-made chain
"templates"). Largely superseded in importance by LangSmith's prompt
management, but still used for pulling/pushing versioned prompts.

**Use cases**
- Sharing a tested prompt across a team or across projects
- Versioning prompts independent of application code

**Pros**
- Decouples prompt iteration from code deploys
- Simple pull/push API

**Limitations**
- Overlaps confusingly with LangSmith's own prompt hub/playground (the
  ecosystem hasn't fully consolidated this)
- Adds another moving part for what a config file or DB row could do for
  many teams

---

## How the pieces fit together

- **Prototyping a RAG bot or simple tool-caller** → LangChain core (chains/
  LCEL) is usually enough.
- **Building an agent with real control flow, loops, or multiple
  cooperating agents** → reach for LangGraph instead of LangChain's legacy
  AgentExecutor.
- **Anything going to production** → wire in LangSmith early; retrofitting
  observability after things break is much harder.
- **Deploying a LangGraph agent as a real service** → LangGraph Platform, or
  hand-roll deployment (FastAPI/containers) if you don't want the managed
  dependency.

## Ecosystem-wide caveats

- **Vendor gravity**: the more of the stack you adopt (LangChain → LangGraph
  → LangSmith → LangGraph Platform), the harder it is to leave; each layer's
  best features assume the others are present.
- **Fast-moving API surface**: breaking changes across minor versions have
  been common historically — pin versions and expect migration work.
- **Not always the simplest option**: for a single well-scoped LLM call or a
  small agent, direct use of a provider SDK (or a lighter framework) is often
  less code and easier to reason about than adopting the full ecosystem.
