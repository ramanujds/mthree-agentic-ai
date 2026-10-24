"""Capstone R2 - typed, safe tools. These are plain functions so they work with Pydantic-AI (tools=[...]), LlamaIndex (FunctionTool)
or your own loop. Keep them NARROW, validated, deterministic, idempotent where they have side effects, and PII-safe.

Errors: raise harness.types.ToolError(code, message) with EXACTLY these codes
    invalid_account_id  (must match ACC-dddd; EVERY tool that takes an account_id checks this first, escalate_ticket included)      account_not_found     unknown_fee_type     invalid_quantity (<1 or >1000)
    unknown_plan        invalid_priority (not P1/P2/P3)    invalid_reason (empty or >300 chars)

lookup_account_status(db, account_id) -> AccountStatus
    Never return holder name, email, phone or the full account number. masked_account_number keeps only the last 4 digits ("************1234").
calculate_fee(fee_type, quantity=1, plan=None) -> FeeQuote
    Use harness.backends.load_fee_schedule(). plan in {None,"business_current","premier_saver"}; free_allowance applies to domestic_wire only.
    total = unit_fee * (quantity - free_quantity).
escalate_ticket(store, account_id, reason, priority) -> Ticket
    IDEMPOTENT: the same (account_id, normalised reason, priority) must return the existing ticket (created_new=False) and never add a second one.
    ticket_id format "TCK-0001", "TCK-0002", ...
search_policy(retriever, query, k=4) -> list[{"doc_id","chunk_id","text"}]    (RAG-as-a-tool)
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from harness.types import ToolError            # noqa: F401  (raise this)
from harness.backends import load_fee_schedule  # noqa: F401


class AccountStatus(BaseModel):
    account_id: str
    product: str
    status: str
    masked_account_number: str
    freeze_reason: Optional[str] = None


class FeeQuote(BaseModel):
    fee_type: str
    unit_fee: float
    quantity: int
    free_quantity: int
    total: float
    schedule_id: str


class Ticket(BaseModel):
    ticket_id: str
    account_id: str
    reason: str
    priority: str
    created_new: bool


def lookup_account_status(db, account_id: str) -> AccountStatus:
    raise NotImplementedError("capstone R2: lookup_account_status")


def calculate_fee(fee_type: str, quantity: int = 1, plan: Optional[str] = None) -> FeeQuote:
    raise NotImplementedError("capstone R2: calculate_fee")


def escalate_ticket(store, account_id: str, reason: str, priority: str) -> Ticket:
    raise NotImplementedError("capstone R2: escalate_ticket")


def search_policy(retriever, query: str, k: int = 4) -> list:
    raise NotImplementedError("capstone R2: search_policy")
