from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ToolError(Exception):
    """Structured, user-safe tool error. code is machine readable; message is human readable."""
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message

    def to_dict(self):
        return {"error": self.code, "message": self.message}


class AgentResult(BaseModel):
    intent: Literal["account_status", "fee_quote", "escalation", "policy_question", "transfer", "unknown"]
    answer: str
    tools_used: list[str] = []
    sources: list[str] = []
    needs_human: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    approval_id: str
    request_id: str
    from_account: str
    beneficiary: str
    amount: float
    reason: str


class ApprovalDecision(BaseModel):
    approved: bool
    approver: str = "human"
    note: str = ""


class RunResult(BaseModel):
    route: Literal["retrieval", "transaction", "escalation", "unknown"]
    status: Literal["completed", "pending_approval", "rejected", "denied", "failed"]
    answer: str = ""
    steps: list[str] = []
    approval: Optional[ApprovalRequest] = None
