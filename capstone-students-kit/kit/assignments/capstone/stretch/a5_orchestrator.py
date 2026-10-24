"""Stretch S2 - multi-agent orchestration with a human-in-the-loop gate.
Structure it as a router + specialised agents (retrieval agent, transaction agent, escalation agent). LlamaIndex Workflows (event-driven
steps) is the expected style - wrap the async workflow in asyncio.run() inside run()/resume() - but the contract below is what is auto-graded
and plain Python is accepted if you justify it. Everything is offline: no LLM is required for the routing/approval logic itself.

Orchestrator(deps, approver=None)
    deps     : harness.deps.Deps (llm, db, ledger, tickets, retriever, user_role)
    approver : callable(ApprovalRequest) -> ApprovalDecision, simulating the human reviewer. If None, nothing is approved automatically:
               the run stops with status "pending_approval" and can be continued later with resume().

run(request: str, request_id: str, user_role: str = "support_agent") -> harness.types.RunResult
    route   : "retrieval" (questions about policy/fees) | "transaction" (transfer/send/move money) | "escalation" (escalate/fraud/complaint)
    Rules for the transaction route (from policy SEC-001 / PAY-001):
      * only role "payments_agent" may move money; any other role -> status "denied", nothing touched, approver never called
      * human approval is REQUIRED when amount > 1000 (exactly 1000 is fine) OR the beneficiary is not in ledger.known_beneficiaries(account)
      * approved -> execute via ledger.post_transfer; rejected -> status "rejected", no money moves; no approver -> "pending_approval"
      * check funds when you EXECUTE (not only when you ask): insufficient funds -> status "failed", no posting
    Idempotency: run() with a request_id you have already processed must return the same result and must not post twice.
    Context isolation: the retrieval route must not touch deps.db / deps.ledger; the transaction route must not call the retriever.
    steps: human-readable list of what happened, e.g. ["route:transaction","authorize:ok","approval:required","approval:approved","posted"].
           Any run that required approval MUST contain a step starting with "approval".
    approval: the ApprovalRequest (approval_id, request_id, from_account, beneficiary, amount, reason) when approval was needed.

resume(approval_id: str, decision: ApprovalDecision) -> RunResult
    Continue a "pending_approval" run. Resuming twice must not post twice. Unknown approval_id -> status "failed".
"""
from __future__ import annotations
from harness.types import ApprovalDecision, ApprovalRequest, RunResult


class Orchestrator:
    def __init__(self, deps, approver=None):
        raise NotImplementedError("capstone: Orchestrator.__init__")

    def run(self, request: str, request_id: str, user_role: str = "support_agent") -> RunResult:
        raise NotImplementedError("capstone: run")

    def resume(self, approval_id: str, decision: ApprovalDecision) -> RunResult:
        raise NotImplementedError("capstone: resume")
