"""Capstone evidence gate: does the evidence exist, is it parseable, does the app run offline and degrade gracefully?
Quality is judged by the trainer's rubric (architecture, observability, reliability, business fit, documentation, demo)."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
from .framework import KIT


def run(ctx):
    d = ctx.dir
    words = lambda p: len(p.read_text(encoding="utf-8", errors="replace").split()) if p.exists() else 0

    uniq = lambda p: len({w.lower() for w in p.read_text(encoding="utf-8", errors="replace").split()}) if p.exists() else 0

    def exists(rel, min_words=0):
        p = d / rel
        ok = p.exists() and words(p) >= min_words and uniq(p) >= 0.35 * min_words      # filler text repeating the same words does not count
        return ok, f"{rel}: {'missing' if not p.exists() else str(words(p)) + ' words, ' + str(uniq(p)) + ' distinct (min ' + str(min_words) + ' words, real content)'}"

    ctx.check("A8.1 README (>= 200 words)", 3, lambda: exists("README.md", 200))

    def arch():
        p = d / "docs" / "architecture.md"
        diag = any(list((d / "docs").glob(f"*.{e}")) for e in ("svg", "png", "drawio")) or (p.exists() and "```mermaid" in p.read_text(encoding="utf-8", errors="replace"))
        return (0.5 * (words(p) >= 200) + 0.5 * diag), "needs >= 200 words and a diagram (mermaid block, .svg, .png or .drawio)"
    ctx.check("A8.2 architecture document + diagram", 3, arch)
    ctx.check("A8.3 business case", 2, lambda: exists("docs/business_case.md", 120))

    def runbook():
        p = d / "docs" / "runbook.md"
        t = p.read_text(encoding="utf-8", errors="replace").lower() if p.exists() else ""
        keys = ["health", "troubleshoot", "escalat", "rollback", "known issue"]
        return (sum(k in t for k in keys) / 5) * (1 if words(p) >= 300 else 0.5), "needs >= 300 words and sections: health check, troubleshooting, escalation, rollback, known issues"
    ctx.check("A8.4 runbook", 3, runbook)
    ctx.check("A8.5 governance summary", 3, lambda: exists("docs/governance_summary.md", 150))

    def reports():
        out = []
        for n in ("eval_baseline.json", "eval_after.json"):
            try:
                j = json.loads((d / "reports" / n).read_text(encoding="utf-8", errors="replace")); out.append("metrics" in j and "latency_ms" in j and "sim_cost_usd" in j)
            except Exception:
                out.append(False)
        return sum(out) / 2, "both files must be run_eval() outputs"
    ctx.check("A8.6 baseline and after evaluation reports", 4, reports)

    def traces():
        best = 0
        for f in (d / "traces").glob("*.jsonl") if (d / "traces").exists() else []:
            try:
                sp = [json.loads(l) for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
                if len(sp) >= 5 and all({"name", "start_ms", "end_ms"} <= set(s) for s in sp): best = 1
            except Exception:
                pass
        return best, "traces/*.jsonl with >= 5 spans (name,start_ms,end_ms)"
    ctx.check("A8.7 exported trace", 3, traces)

    def audit():
        p = d / "audit" / "audit.jsonl"
        if not p.exists(): return 0, "audit/audit.jsonl missing"
        import importlib.util
        a7 = d if (d / "a7_audit.py").exists() else d.parent / "a7_hardening"
        sys.path.insert(0, str(a7))
        spec = importlib.util.spec_from_file_location("cap_audit", a7 / "a7_audit.py"); mod = importlib.util.module_from_spec(spec); sys.modules["cap_audit"] = mod; spec.loader.exec_module(mod)
        v = mod.AuditLog(p).verify()
        return (v["ok"] and v["entries"] >= 3), f"verify -> {v} (needs >= 3 entries)"
    ctx.check("A8.8 audit log verifies", 3, audit)

    ctx.check("A8.9 game-day report", 3, lambda: exists("gameday/gameday_report.md", 120))
    ctx.check("A8.10 recorded demo reference + script", 2, lambda: exists("demo/demo.md", 60))

    def app(fault=None):
        env = dict(os.environ, PYTHONPATH=str(KIT))
        env.pop("GAMEDAY_FAULT", None)
        if fault: env["GAMEDAY_FAULT"] = fault
        p = d / "app.py"
        if not p.exists(): return 0, "app.py missing"
        r = subprocess.run([sys.executable, str(p), "--demo"], capture_output=True, text=True, env=env, timeout=60, cwd=str(d))
        out = (r.stdout + r.stderr).lower()
        if fault: return (0.5 * (r.returncode == 0) + 0.5 * ("degraded" in out or "fallback" in out)), f"exit={r.returncode}; must exit 0 and mention degraded/fallback"
        return (r.returncode == 0), f"exit={r.returncode} {r.stderr[-200:]}"
    ctx.check("A8.11 `python app.py --demo` runs offline and exits 0", 5, lambda: app(), seconds=70)
    ctx.check("A8.12 app degrades gracefully under an injected tool outage", 6, lambda: app("tool_outage"), seconds=70)
