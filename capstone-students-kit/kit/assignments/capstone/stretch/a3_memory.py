"""Stretch S1b - agent memory with a hard token budget.

ConversationMemory(max_tokens, summarizer)
    summarizer : callable(list[message dict]) -> str     (the harness provides harness.text.extractive_summary; any callable works)
    add(role, content)         - append a turn (role: "user" | "assistant")
    pin(key, value)            - a fact that must NEVER be dropped (e.g. account_id, preferred_language)
    get_context() -> list[dict]  messages ready to send to a model:
         * first message: role="system" containing every pinned fact and, once older turns were dropped, a running summary of them
         * then as many of the MOST RECENT turns as fit, verbatim and in order
         * total harness.text.count_tokens(content) over all returned messages must be <= max_tokens
    Efficiency: do not call the summarizer on every add(); call it only when turns actually fall out of the window, and not again
    when get_context() is called twice with no new turns.
"""
from __future__ import annotations


class ConversationMemory:
    def __init__(self, max_tokens, summarizer):
        raise NotImplementedError("capstone: ConversationMemory")

    def add(self, role, content):
        raise NotImplementedError

    def pin(self, key, value):
        raise NotImplementedError

    def get_context(self):
        raise NotImplementedError
