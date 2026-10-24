"""Capstone - the Meridian Support Assistant: ONE application that wires every part of the training together.

You decide the architecture. The grader only needs this contract (everything runs OFFLINE with the harness RuleLLM):

    build_app(deps=None, audit_path=None, trace_path=None) -> CapstoneApp
        deps         harness.deps.Deps; if None use make_deps(). The app must use deps.llm, deps.retriever, deps.db, deps.tickets
                     (the grader injects faults and hold-out data through them).
        audit_path   hash-chained audit log file (a7_audit.AuditLog) - default audit/audit.jsonl
        trace_path   JSONL spans (a6_evals.Tracer) - default traces/app_trace.jsonl, rewritten/appended after every request

    CapstoneApp.deps                                   the Deps in use
    CapstoneApp.handle(request: str, role: str = "support_agent") -> AgentResult (or a dict that validates as one)

What handle() must do for every request (the integration checks test each of these):
    1. authorise the action for `role` (a7_guard.authorize) - a role that may not act gets needs_human=True and NO side effect
    2. retrieve through your RAG layer and keep retrieved text DATA-ONLY: poisoned documents must not steer the model
    3. answer with the right tool(s) and cite sources (a4_agent / a2_rag); never return raw PII in the answer
    4. write one audit entry per request and trace spans (>= 3 per request, with name/start_ms/end_ms)
    5. survive faults: with GAMEDAY_FAULT=tool_outage (or inject("tool_outage")) return a valid result that says it is degraded
       and hands over to a human - no exception, no crash - and recover when the fault clears

    python app.py --demo   runs a scripted scenario OFFLINE and exits 0; with GAMEDAY_FAULT=tool_outage it still exits 0 and prints "degraded"

Reuse the module stubs in this folder (a2_rag.py, a4_tools.py, a4_agent.py, a6_evals.py, a7_*.py). Optional stretch modules live in stretch/.
"""
from __future__ import annotations
import pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
for _p in (HERE, HERE.parents[1]):      # lets `python app.py --demo` find your modules (HERE) and the harness (kit root) - keep this
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def build_app(deps=None, audit_path=None, trace_path=None):
    raise NotImplementedError("capstone: build_app")


if __name__ == "__main__":
    raise SystemExit("implement the --demo scenario")
