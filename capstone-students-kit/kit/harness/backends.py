"""Fake back-office systems. All data is synthetic."""
from __future__ import annotations
import copy, json
from . import DATA_DIR
from . import faults


class AccountDB:
    """Raw account records INCLUDING PII. A safe tool must never leak these fields straight to the model/user."""
    def __init__(self):
        self._a = copy.deepcopy(json.loads((DATA_DIR / "accounts.json").read_text(encoding="utf-8", errors="replace"))["accounts"])
        self.lookups = 0

    def get(self, account_id: str):
        faults.maybe_fail("accountdb")
        self.lookups += 1
        r = self._a.get(account_id)
        return copy.deepcopy(r) if r else None


class TicketStore:
    def __init__(self):
        self.tickets: list[dict] = []

    def add(self, ticket: dict) -> dict:
        self.tickets.append(ticket)
        return ticket

    def all(self):
        return list(self.tickets)


class Ledger:
    """Money movement. post_transfer has NO idempotency of its own - callers must protect it."""
    def __init__(self, db: AccountDB):
        self.db = db
        self.balances = {k: v["balance"] for k, v in db._a.items()}
        self.postings: list[dict] = []

    def balance(self, account_id: str) -> float:
        return self.balances[account_id]

    def known_beneficiaries(self, account_id: str) -> list[str]:
        return list(self.db._a[account_id]["beneficiaries"])

    def post_transfer(self, account_id: str, beneficiary: str, amount: float) -> dict:
        if amount > self.balances[account_id]:
            raise ValueError("insufficient funds")
        self.balances[account_id] -= amount
        p = {"account": account_id, "beneficiary": beneficiary, "amount": amount}
        self.postings.append(p)
        return p


def load_fee_schedule() -> dict:
    return json.loads((DATA_DIR / "fee_schedule_2025.json").read_text(encoding="utf-8", errors="replace"))
