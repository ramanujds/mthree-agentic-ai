# Progress Check — LLMs, Agentic AI and RAG

## 1. LLM Fundamentals

**Q1.1** At its core, what does a large language model do when it generates text?

**Q1.2** What is a token, and why do tokens matter to an engineer?

**Q1.3** What is the context window, and what happens when a conversation exceeds it?

**Q1.4** What does temperature control? When would you set it low?

**Q1.5** Why do LLMs hallucinate?

**Q1.6** What is the knowledge cutoff, and how do systems work around it?

**Q1.7** Distinguish a base model from an instruction-tuned (chat) model.

**Q1.8** What are the system, user and assistant roles in a chat request?

**Q1.9** Why are LLM APIs described as stateless, and what does that mean for application design?

## 2. Prompting and Structured Output

**Q2.1** Distinguish zero-shot and few-shot prompting.

**Q2.2** What is chain-of-thought prompting and why does it help?

**Q2.3** Why is structured output (e.g. JSON matching a schema) important in LLM applications?

**Q2.4** Name three characteristics of a good system prompt for a production assistant.

**Q2.5** What is prompt injection?

## 3. Agentic AI — Core Concepts

**Q3.1** What makes a system an "agent" rather than a single LLM call?

**Q3.2** Describe the core agent loop.

**Q3.3** Does the LLM execute a tool? Explain how tool calling works.

**Q3.4** Why do tool descriptions matter so much?

**Q3.5** What is the ReAct pattern?

**Q3.6** Compare ReAct with plan-and-execute.

**Q3.7** Distinguish a **workflow** from an **agent**. When should you prefer a workflow?

**Q3.8** Name and briefly describe four common workflow patterns.

**Q3.9** Distinguish short-term and long-term memory in an agent.

**Q3.10** What are the benefits and costs of a multi-agent system?

**Q3.11** What is MCP (Model Context Protocol), and what problem does it solve?

## 4. Agents in Production

**Q4.1** Name five common failure modes of agents.

**Q4.2** List four ways a production agent deployment differs from a traditional web application.

**Q4.3** Why is observability (tracing) essential for agents, and what should a trace capture?

**Q4.4** How do you control cost and latency in an agent?

**Q4.5** Why run agent tools — especially code execution — in a sandbox such as a container?

**Q4.6** An agent for a bank's operations team can read customer records and initiate refunds. Design three guardrails.

**Q4.7** A colleague says: "Let's make everything an agent — it's more flexible." How do you respond?

## 5. RAG Fundamentals (Week 3)

**Q5.1** What problem does Retrieval-Augmented Generation solve?

**Q5.2** Describe the two pipelines in a RAG system.

**Q5.3** What is an embedding?

**Q5.4** What goes wrong if chunks are too large or too small?

**Q5.5** Why must the same embedding model be used for indexing and querying?

**Q5.6** Why combine keyword (BM25) and semantic search?

## 6. RAG Beyond the Basics (Week 4)

**Q6.1** What is a re-ranker and why add it after vector search?

**Q6.2** Name two query-transformation techniques and what they help with.

**Q6.3** What is the "lost in the middle" problem?

**Q6.4** When would you choose RAG over fine-tuning, and vice versa?

**Q6.5** A RAG system gives a wrong answer. How do you tell whether retrieval or generation is at fault?

**Q6.6** Define **faithfulness** (groundedness).

## 7. Putting It Together — Bridge to Week 5

**Q7.1** How does "Agentic RAG" differ from the RAG pipeline you built in Weeks 3–4?

**Q7.2** Why is prompt injection a bigger concern in RAG and agent systems than in a plain chatbot?

**Q7.3** The compliance team wants an assistant over 10,000 internal policy PDFs. Some questions are simple lookups ("What is the gift limit?"); others require comparing several policies ("How do the 2025 and 2026 travel policies differ for contractors?"). Propose a design.

**Q7.4** Your agent passes every demo but users report it sometimes "confidently makes things up" after long conversations. Give three likely causes and fixes.
