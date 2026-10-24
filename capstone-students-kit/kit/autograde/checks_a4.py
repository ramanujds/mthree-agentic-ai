from __future__ import annotations
import re
from harness.deps import make_deps
from harness.types import AgentResult, ToolError

PII = ["4111111111111234", "asha.verma@example.com", "Asha Verma", "+44 7700 900101"]


def _raises(fn, code):
    try:
        fn()
    except ToolError as e:
        return e.code == code
    except Exception:
        return False
    return False


def run(ctx):
    t = ctx.load("a4_tools.py")
    ag = ctx.load("a4_agent.py")

    def validation():
        d = make_deps()
        cases = [lambda: t.lookup_account_status(d.db, "ACC-12") , lambda: t.lookup_account_status(d.db, "ACC-9999"), lambda: t.calculate_fee("bogus"),
                 lambda: t.calculate_fee("overdraft", 0), lambda: t.calculate_fee("overdraft", 5000), lambda: t.calculate_fee("domestic_wire", 1, "gold_plan"),
                 lambda: t.escalate_ticket(d.tickets, "ACC-1001", "x", "P9"), lambda: t.escalate_ticket(d.tickets, "ACC-1001", "   ", "P1"),
                 lambda: t.escalate_ticket(d.tickets, "1001", "x", "P1")]
        codes = ["invalid_account_id", "account_not_found", "unknown_fee_type", "invalid_quantity", "invalid_quantity", "unknown_plan", "invalid_priority", "invalid_reason", "invalid_account_id"]
        ok = [_raises(c, k) for c, k in zip(cases, codes)]
        names = ["lookup 'ACC-12'", "lookup ACC-9999", "fee 'bogus'", "fee quantity 0", "fee quantity 5000", "fee plan 'gold_plan'", "escalate priority P9", "escalate blank reason", "escalate account '1001'"]
        return sum(ok) / len(ok), "wrong or missing error code for: " + str([f"{names[i]} (expected {codes[i]})" for i, v in enumerate(ok) if not v])
    ctx.check("A4.1 tools validate input and raise ToolError with the specified codes", 6, validation)

    def fees():
        a = t.calculate_fee("domestic_wire", 3)
        b = t.calculate_fee("domestic_wire", 21, "business_current")
        c = t.calculate_fee("domestic_wire", 7, "premier_saver")
        d = t.calculate_fee("international_wire")
        e = t.calculate_fee("overdraft", 2, "business_current")   # allowance applies to domestic_wire only
        ok = [a.total == 45.0, (b.total, b.free_quantity) == (15.0, 20), (c.total, c.free_quantity) == (30.0, 5), d.total == 40.0 and d.schedule_id == "FEES-001", e.total == 50.0 and e.free_quantity == 0]
        return sum(ok) / 5, f"{[x for x in ok]}"
    ctx.check("A4.2 calculate_fee uses the 2025 schedule and free allowances correctly", 5, fees)

    def lookup():
        d = make_deps()
        r = t.lookup_account_status(d.db, "ACC-1001")
        dump = str(r.model_dump())
        leak = [p for p in PII if p in dump]
        ok = r.masked_account_number == "************1234" and r.status == "active" and not leak
        f = t.lookup_account_status(d.db, "ACC-1003")
        return 0.7 * ok + 0.3 * (f.status == "frozen" and f.freeze_reason == "KYC review"), f"leaked: {leak}; masked={r.masked_account_number}"
    ctx.check("A4.3 lookup_account_status is PII-safe (masked number, no name/email/phone)", 5, lookup)

    def idem():
        d = make_deps()
        a = t.escalate_ticket(d.tickets, "ACC-1002", "Suspected fraud on card", "P1")
        b = t.escalate_ticket(d.tickets, "ACC-1002", "  suspected FRAUD on card ", "P1")
        c = t.escalate_ticket(d.tickets, "ACC-1002", "Suspected fraud on card", "P2")
        ok = [a.ticket_id == "TCK-0001" and a.created_new, b.ticket_id == a.ticket_id and not b.created_new, c.created_new and c.ticket_id == "TCK-0002", len(d.tickets.all()) == 2]
        return sum(ok) / 4, str(ok)
    ctx.check("A4.4 escalate_ticket is idempotent", 4, idem)

    def scen(request, **expect):
        def fn():
            d = make_deps()
            r = ag.handle(request, d)
            r = r if isinstance(r, AgentResult) else AgentResult.model_validate(r)
            ans, checks = r.answer.lower(), []
            if "intent" in expect: checks.append(r.intent == expect["intent"])
            if "tools" in expect: checks.append(all(x in r.tools_used for x in expect["tools"]))
            for w in expect.get("contains", []): checks.append(w.lower() in ans)
            if "needs_human" in expect: checks.append(r.needs_human == expect["needs_human"])
            if "max_conf" in expect: checks.append(r.confidence <= expect["max_conf"])
            if expect.get("no_pii", True): checks.append(not any(p.lower() in ans for p in PII) and not re.search(r"\b\d{12,}\b", ans))
            if "sources" in expect: checks.append(bool(set(r.sources) & set(expect["sources"])))
            return sum(checks) / len(checks), f"got intent={r.intent} tools={r.tools_used} needs_human={r.needs_human} conf={r.confidence} answer={r.answer[:140]!r}"
        return fn
    ctx.check("A4.5 account status request", 3, scen("What is the status of ACC-1001?", intent="account_status", tools=["lookup_account_status"], contains=["active"], needs_human=False))
    ctx.check("A4.6 fee quote request", 3, scen("How much is an international wire fee?", intent="fee_quote", tools=["calculate_fee"], contains=["40"], needs_human=False))
    ctx.check("A4.7 frozen account -> human follow-up", 3, scen("What is the status of ACC-1003?", intent="account_status", contains=["frozen"], needs_human=True))
    ctx.check("A4.8 fraud escalation creates exactly one ticket (even if asked twice)", 3, lambda: _esc(ag))
    ctx.check("A4.9 policy question uses RAG-as-a-tool and cites sources", 4,
              scen("Who must approve a $30,000 wire initiated at the Harbor Street branch?", intent="policy_question", tools=["search_policy"], sources=["ORG-001", "RISK-001"]))
    ctx.check("A4.10 unknown account handled gracefully, low confidence", 3, scen("What is the status of ACC-9999?", contains=["could not complete"], max_conf=0.49))

    def valid_out():
        r = ag.handle("What is the status of ACC-1004?", make_deps())
        AgentResult.model_validate(r if isinstance(r, dict) else r.model_dump())
        return True
    ctx.check("A4.11 always returns a valid AgentResult", 1, valid_out)

    def framework():
        src = (ctx.dir / "a4_agent.py").read_text(encoding="utf-8", errors="replace")
        fw = [n for n in ("pydantic_ai", "llama_index") if n in src]
        j = ctx.dir / "framework_choice.md"
        return bool(fw) or j.exists(), f"frameworks imported: {fw}; framework_choice.md present: {j.exists()}"
    ctx.check("A4.12 framework use / justification (informational)", 0, framework)


def _esc(ag):
    d = make_deps()
    q = "Please escalate: fraud suspected on ACC-1002"
    r1 = ag.handle(q, d); r2 = ag.handle(q, d)
    r1 = r1 if isinstance(r1, AgentResult) else AgentResult.model_validate(r1)
    ok = [r1.intent == "escalation", r1.needs_human, "escalate_ticket" in r1.tools_used, len(d.tickets.all()) == 1, "TCK-0001" in r1.answer]
    return sum(ok) / 5, str(ok)
