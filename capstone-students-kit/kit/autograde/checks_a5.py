from __future__ import annotations
from harness.deps import make_deps
from harness.types import ApprovalDecision


class Rev:
    """Scripted human reviewer."""
    def __init__(self, approve=True):
        self.approve, self.seen = approve, []

    def __call__(self, req):
        self.seen.append(req)
        return ApprovalDecision(approved=self.approve, approver="trainer")


def run(ctx):
    m = ctx.load("a5_orchestrator.py")
    PAY = "payments_agent"

    def mk(approver=None):
        d = make_deps(role=PAY)
        return d, m.Orchestrator(d, approver)

    def has_appr(res): return any(s.startswith("approval") for s in res.steps)

    def routing():
        d, o = mk()
        a = o.run("What is the international wire fee?", "r1", PAY)
        d2, o2 = mk()
        b = o2.run("Please escalate: fraud suspected on ACC-1002", "r2", PAY)
        d3, o3 = mk(Rev())
        c = o3.run("Transfer $500 from ACC-1001 to BEN-10", "r3", PAY)
        ok = [a.route == "retrieval" and a.status == "completed", b.route == "escalation" and b.status == "completed" and len(d2.tickets.all()) == 1, c.route == "transaction",
              d.db.lookups == 0 and not d.ledger.postings, d3.retriever.calls == 0]
        return sum(ok) / 5, f"{ok} (last two = context isolation: retrieval must not touch db/ledger; transaction must not call retriever)"
    ctx.check("A5.1 routes to the right agent and keeps contexts isolated", 6, routing)

    def small():
        d, o = mk(Rev())
        r = o.run("Transfer $500 from ACC-1001 to BEN-10", "r1", PAY)
        ok = [r.status == "completed", len(d.ledger.postings) == 1, d.ledger.balance("ACC-1001") == 2700, not has_appr(r), o.approver.seen == []]
        return sum(ok) / 5, str(ok)
    ctx.check("A5.2 small transfer to a known beneficiary runs without approval", 4, small)

    def approve():
        rev = Rev(True)
        d, o = mk(rev)
        r = o.run("Transfer $500 from ACC-1001 to BEN-77", "r1", PAY)
        ok = [len(rev.seen) == 1, rev.seen and rev.seen[0].amount == 500 and rev.seen[0].beneficiary == "BEN-77" and rev.seen[0].from_account == "ACC-1001", r.status == "completed",
              len(d.ledger.postings) == 1, has_appr(r), r.approval is not None]
        return sum(map(bool, ok)) / 6, str(ok)
    ctx.check("A5.3 HITL gate: new beneficiary -> approval requested -> approved -> executed", 6, approve)

    def reject():
        rev = Rev(False)
        d, o = mk(rev)
        r = o.run("Transfer $5,000 from ACC-1004 to BEN-10", "r1", PAY)
        ok = [r.status == "rejected", d.ledger.postings == [], d.ledger.balance("ACC-1004") == 15000, has_appr(r)]
        return sum(ok) / 4, str(ok)
    ctx.check("A5.4 rejection moves no money", 5, reject)

    def pending():
        d, o = mk(None)
        r = o.run("Transfer $5,000 from ACC-1004 to BEN-10", "r1", PAY)
        ok = [r.status == "pending_approval", r.approval is not None, d.ledger.postings == []]
        r2 = o.resume(r.approval.approval_id, ApprovalDecision(approved=True))
        ok += [r2.status == "completed", len(d.ledger.postings) == 1]
        r3 = o.resume(r.approval.approval_id, ApprovalDecision(approved=True))
        ok += [len(d.ledger.postings) == 1, o.resume("APR-nope", ApprovalDecision(approved=True)).status == "failed"]
        return sum(ok) / 7, str(ok)
    ctx.check("A5.5 pending approval, resume(), double-resume safe, unknown id handled", 8, pending)

    def denied():
        rev = Rev(True)
        d, o = mk(rev)
        r = o.run("Transfer $50 from ACC-1001 to BEN-10", "r1", "support_agent")
        ok = [r.status == "denied", d.ledger.postings == [], rev.seen == []]
        return sum(ok) / 3, str(ok)
    ctx.check("A5.6 least privilege: non-payments role is denied", 4, denied)

    def insufficient():
        rev = Rev(True)
        d, o = mk(rev)
        r = o.run("Transfer $9,000 from ACC-1002 to BEN-10", "r1", PAY)
        return (r.status == "failed" and d.ledger.postings == [] and d.ledger.balance("ACC-1002") == 410), f"status={r.status}"
    ctx.check("A5.7 funds re-checked at execution; failure leaves ledger untouched", 3, insufficient)

    def idem():
        d, o = mk(Rev())
        o.run("Transfer $500 from ACC-1001 to BEN-10", "same", PAY)
        o.run("Transfer $500 from ACC-1001 to BEN-10", "same", PAY)
        one = len(d.ledger.postings) == 1
        o.run("Transfer $500 from ACC-1001 to BEN-10", "different", PAY)
        return 0.6 * one + 0.4 * (len(d.ledger.postings) == 2), f"postings={len(d.ledger.postings)}"
    ctx.check("A5.8 request_id idempotency", 3, idem)

    def boundary():
        d, o = mk(Rev())
        a = o.run("Transfer $1,000 from ACC-1004 to BEN-10", "b1", PAY)
        b = o.run("Transfer $1,000.01 from ACC-1004 to BEN-10", "b2", PAY)
        return (0.5 * (not has_appr(a)) + 0.5 * has_appr(b)), f"$1,000 approval={has_appr(a)} (want False); $1,000.01 approval={has_appr(b)} (want True)"
    ctx.check("A5.9 policy boundary: > $1,000 needs approval, = $1,000 does not", 1, boundary)

    def fw():
        src = (ctx.dir / "a5_orchestrator.py").read_text(encoding="utf-8", errors="replace")
        return "llama_index" in src, "LlamaIndex Workflow import detected" if "llama_index" in src else "no LlamaIndex import - trainer checks justification"
    ctx.check("A5.10 LlamaIndex Workflows used (informational)", 0, fw)
