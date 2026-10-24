"""Fault injection for Week 8 'game day'. The trainer activates a fault; the learner must notice it through their own
tracing/metrics. Activate via `with inject("tool_outage"):` or the env var GAMEDAY_FAULT=<name>.
Faults: tool_outage | bad_retrieval | cost_spike | slow_tool"""
from __future__ import annotations
import os, time
from contextlib import contextmanager

FAULTS = ("tool_outage", "bad_retrieval", "cost_spike", "slow_tool")
_active: set[str] = set()


@contextmanager
def inject(name: str):
    assert name in FAULTS, f"unknown fault {name}"
    _active.add(name)
    try:
        yield
    finally:
        _active.discard(name)


def is_active(name: str) -> bool:
    return name in _active or os.environ.get("GAMEDAY_FAULT") == name


def maybe_fail(component: str):
    if is_active("tool_outage"):
        raise ConnectionError(f"{component} unavailable (injected fault)")
    if is_active("slow_tool"):
        time.sleep(0.25)


def degrade_hits(hits: list[dict]) -> list[dict]:
    """bad_retrieval: return the *least* relevant hits (reverse order)."""
    return list(reversed(hits)) if is_active("bad_retrieval") else hits


def token_multiplier() -> int:
    return 8 if is_active("cost_spike") else 1
