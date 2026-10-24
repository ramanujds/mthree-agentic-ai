"""Capstone R3 - the agent. Framework is YOUR choice (Pydantic-AI, LlamaIndex, or hand-rolled) - justify it in docs/decision_log.md.
Offline-friendly: Pydantic-AI's FunctionModel/TestModel and LlamaIndex Workflows need no API key. `deps.llm` (harness RuleLLM) is the
free scripted model; wrap it however your framework needs. See examples/ for tiny runnable wiring examples.

handle(request: str, deps) -> harness.types.AgentResult
    deps: harness.deps.Deps  (llm, db, ledger, tickets, retriever, user_role)
    Required behaviour:
      * use your a4_tools (lookup_account_status, calculate_fee, escalate_ticket, search_policy) - the policy question path MUST call the
        retriever through search_policy (RAG-as-tool) and return the doc ids in `sources`
      * structured output: always return a valid AgentResult (never raise); tools_used lists the tools actually called
      * intent: account_status | fee_quote | escalation | policy_question | transfer | unknown
      * needs_human=True for frozen accounts and for every escalation; confidence < 0.5 when a tool failed
      * the answer text must never contain a full account number, email or phone number
      * unknown/closed/frozen accounts and tool failures must produce a polite explanation, not a stack trace
"""
from __future__ import annotations
from harness.types import AgentResult


def handle(request: str, deps) -> AgentResult:
    raise NotImplementedError("capstone R3: handle")
