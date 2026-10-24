from __future__ import annotations
from harness.llm import RuleLLM, LoopingLLM, ScriptedLLM, FlakyLLM

SPECS = [{"name": n, "description": n, "parameters": {}} for n in ("lookup_account_status", "calculate_fee")]


def _tools(log):
    def lookup_account_status(account_id):
        log.append(("lookup", account_id)); return {"account_id": account_id, "status": "active"}

    def calculate_fee(fee_type, quantity=1):
        log.append(("fee", fee_type)); return {"fee_type": fee_type, "total": 40.0 * quantity}
    return {"lookup_account_status": lookup_account_status, "calculate_fee": calculate_fee}


def run(ctx):
    m = ctx.load("a1_react.py")
    Q = "Customer on ACC-1002 asks the cost of an international wire; is the account active?"

    def happy():
        log = []
        r = m.run_react(Q, RuleLLM(), _tools(log), SPECS, max_steps=5)
        ok = [r["status"] == "completed", [s["tool"] for s in r["steps"]] == ["lookup_account_status", "calculate_fee"],
              r["answer"] and "active" in r["answer"].lower() and "40" in r["answer"], log == [("lookup", "ACC-1002"), ("fee", "international_wire")]]
        return sum(map(bool, ok)) / 4, f"status={r['status']} tools={[s['tool'] for s in r['steps']]}"
    ctx.check("A1.1 completes a 2-tool task correctly (status, order, answer)", 8, happy)

    def trace_shape():
        r = m.run_react(Q, RuleLLM(), _tools([]), SPECS)
        keys = {"step", "tool", "args", "observation", "error"}
        ok = all(keys <= set(s) for s in r["steps"]) and r["steps"] and r["usage"]["tokens_in"] > 0 and r["usage"]["tokens_out"] > 0 and "stopped_reason" in r
        return bool(ok), "each step needs step/tool/args/observation/error; usage summed from llm usage"
    ctx.check("A1.2 structured trace + token usage", 5, trace_shape)

    def unknown_tool():
        llm = ScriptedLLM([{"content": None, "tool_calls": [{"id": "c1", "name": "nonexistent_tool", "arguments": {}}]}, {"content": "done"}])
        r = m.run_react("x", llm, {}, SPECS)
        return (r["status"] == "completed" and r["steps"][0]["error"] is not None and r["answer"] == "done"), f"{r['status']}"
    ctx.check("A1.3 unknown tool does not crash the loop", 5, unknown_tool)

    def tool_exception():
        def boom(account_id):
            raise RuntimeError("backend down")
        r = m.run_react("status of ACC-1001?", RuleLLM(), {"lookup_account_status": boom}, SPECS)
        ok = r["status"] == "completed" and r["steps"] and r["steps"][0]["error"] and "could not complete" in (r["answer"] or "").lower()
        return bool(ok), "error must be passed to the model as JSON {'error','message'}; the loop continues"
    ctx.check("A1.4 tool exception fed back to model as structured error", 6, tool_exception)

    def loop_guard():
        n = []
        tools = {"lookup_account_status": lambda account_id: n.append(1) or {"ok": 1}}
        r = m.run_react("x", LoopingLLM(), tools, SPECS, max_steps=5)
        return (r["status"] == "loop_detected" and len(n) <= 2), f"status={r['status']} executions={len(n)}"
    ctx.check("A1.5 detects a repeated identical tool call", 6, loop_guard)

    def max_steps():
        calls = [{"content": None, "tool_calls": [{"id": f"c{i}", "name": "calculate_fee", "arguments": {"fee_type": "x", "quantity": i}}]} for i in range(20)]
        n = []
        tools = {"calculate_fee": lambda fee_type, quantity: n.append(1) or {"total": quantity}}
        r = m.run_react("x", ScriptedLLM(calls), tools, SPECS, max_steps=3)
        return (r["status"] == "max_steps" and len(n) == 3 and len(r["steps"]) == 3), f"status={r['status']} executions={len(n)}"
    ctx.check("A1.6 enforces max_steps", 6, max_steps)

    def llm_error():
        r = m.run_react("status ACC-1001", FlakyLLM(fail_first=99), _tools([]), SPECS)
        return r["status"] == "error" and r["answer"] is None
    ctx.check("A1.7 model failure returns status 'error'", 4, llm_error)

    def brief():
        p = ctx.dir / "agent_design_brief.md"
        t = p.read_text(encoding="utf-8", errors="replace").lower() if p.exists() else ""
        need = ["problem", "success criteria", "input", "output", "risk", "human", "out of scope"]
        hit = sum(1 for n in need if n in t)
        return (hit / len(need)) * (1 if len(t.split()) >= 250 else 0.5), f"brief has {hit}/{len(need)} required sections, {len(t.split())} words (min 250)"
    ctx.check("A1.8 agent_design_brief.md has required sections", 0, brief)   # informational; scored by trainer rubric
