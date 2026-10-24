"""Capstone R5 - prompt-injection defence, PII redaction, least privilege. Data for self-testing: data/injection_attacks.jsonl,
data/benign_snippets.jsonl, data/pii_labelled.jsonl. The trainer also uses UNSEEN attacks, so do not memorise the list - generalise.

detect_injection(text) -> {"flagged": bool, "patterns": [str]}      target: flag >= 90% of attacks, <= 10% of benign snippets
sanitize_context(text) -> str       remove the flagged sentences, keep the rest (retrieved text is DATA, never instructions)
redact_pii(text) -> str             replace e-mail addresses, phone numbers, 12-19 digit card/account numbers and ddd-dd-dddd national ids with
                                    [REDACTED_EMAIL] / [REDACTED_PHONE] / [REDACTED_CARD] / [REDACTED_ID]; leave everything else byte-for-byte unchanged
                                    (e.g. "$10,000", "ACC-1001", "1 January 2025" must survive)
authorize(role, tool) -> bool       least privilege exactly as in SEC-001 (roles: support_agent, payments_agent, analyst); unknown role or tool -> False
secure_answer(question, deps) -> {"answer": str, "blocked_sources": [doc_id], "findings": [...]}
    End-to-end RAG answer: retrieve with deps.retriever(question, 5); sanitise every chunk BEFORE it reaches the model; record which documents
    contained injection (blocked_sources) and why (findings); call deps.llm.chat(messages, tools) with a system prompt that asks for citations,
    the user question, an assistant tool call to search_policy and a role="tool" message holding the sanitised chunks as JSON
    [{"doc_id","chunk_id","text"}]; finally redact_pii() the model's answer. The harness RuleLLM is deliberately gullible: it obeys instructions
    that reach it inside tool output - your pipeline must make sure none do.
"""
from __future__ import annotations


def detect_injection(text):
    raise NotImplementedError("capstone: implement me")


def sanitize_context(text):
    raise NotImplementedError("capstone: implement me")


def redact_pii(text):
    raise NotImplementedError("capstone: implement me")


def authorize(role, tool):
    raise NotImplementedError("capstone: implement me")


def secure_answer(question, deps):
    raise NotImplementedError("capstone: implement me")
