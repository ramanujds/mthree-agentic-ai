"""Capstone R7 - tamper-evident audit log (append-only JSONL with a hash chain). Policy SEC-001: every AI action is logged with a trace id,
user, timestamp, tools called and sources used; logs are retained 7 years.

AuditLog(path)
    append(trace_id, user, tool, args: dict, sources: list[str], outcome: str) -> dict
        entry fields: seq (0,1,2,...), ts (ISO-8601 string), trace_id, user, tool, args, sources, outcome, prev_hash, hash
        hash = sha256 of the canonical JSON (json.dumps(sort_keys=True, separators=(",", ":"))) of the entry WITHOUT the "hash" field;
        prev_hash = hash of the previous entry ("0"*64 for the first). Opening an existing file continues the chain (seq and prev_hash).
        Every string value inside args - including strings nested inside dicts and lists - is passed through a7_guard.redact_pii BEFORE it is written (no raw PII on disk).
    entries() -> list[dict]
    verify() -> {"ok": bool, "first_bad": int | None, "entries": int}
        recompute every hash and check seq continuity and prev_hash links; first_bad = seq of the first bad entry (a deleted line -> the entry after it).
"""
from __future__ import annotations


class AuditLog:
    def __init__(self, path):
        raise NotImplementedError("capstone: implement me")

    def append(self, trace_id, user, tool, args, sources, outcome):
        raise NotImplementedError("capstone: implement me")

    def entries(self):
        raise NotImplementedError("capstone: implement me")

    def verify(self):
        raise NotImplementedError("capstone: implement me")
