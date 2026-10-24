"""Usage: python -m autograde.run --assignment 2 [--root <repo with assignments/>] [--json out.json] [-v]"""
from __future__ import annotations
import argparse, importlib, json, sys
from pathlib import Path
from .framework import Ctx, KIT

DIRS = {1: "a1_react", 2: "a2_rag", 3: "a3_graphrag", 4: "a4_agent", 5: "a5_multiagent", 6: "a6_observability", 7: "a7_hardening", 8: "a8_capstone"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--assignment", "-a", type=int)
    ap.add_argument("--capstone", action="store_true", help="grade the integrated capstone in assignments/capstone")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(KIT))
    if a.capstone:
        a.assignment = "capstone"
        ctx = Ctx(Path(a.root).resolve(), "capstone")
        mod = importlib.import_module("autograde.checks_cap")
    else:
        ctx = Ctx(Path(a.root).resolve(), DIRS[a.assignment])
        mod = importlib.import_module(f"autograde.checks_a{a.assignment}")
    mod.run(ctx)
    from .zero_cost_scan import scan
    findings = scan(Path(a.root).resolve() / "assignments")
    total, mx = sum(r.points for r in ctx.results), sum(r.max_points for r in ctx.results)
    print(f"\n=== {'CAPSTONE' if a.capstone else 'Assignment ' + str(a.assignment)}: automated checks ===")
    for r in ctx.results:
        if r.max_points == 0 and r.name.startswith("    - ") and not a.v:
            continue                # per-check detail inside a component: shown with -v
        if r.max_points == 0:      # informational evidence for the trainer's rubric, not scored
            print(f"[INFO {'ok     ' if r.frac >= 0.999 else ('partial' if r.frac > 0 else 'missing')}] {r.name}" + (f"  - {r.detail}" if r.frac < 0.999 and r.detail else ""))
            continue
        print(f"[{'PASS' if r.passed else ('PART' if r.points else 'FAIL')}] {r.name}: {r.points}/{r.max_points}" + (f"  - {r.detail}" if r.detail and not r.passed else ""))
    if a.capstone and not a.v and any(r.name.startswith("    - ") and r.frac < 0.999 for r in ctx.results):
        print("\n(Some checks inside the components above are not passing yet. Run again with -v to see each one and why.)")
    print(f"\nAUTOMATED SCORE: {total:.1f}/{mx:.0f}")
    if a.capstone:
        g = getattr(mod, "GATE", {})
        print(f"EVIDENCE GATE: {'PASS' if g.get('ok') else 'FAIL'} ({g.get('score', 0):.1f}/{g.get('max', 0):.0f}, needs >= {g.get('need', 0):.0f}); STRETCH BONUS: {g.get('bonus', 0):.1f}/5")
    fails = [f for f in findings if f["severity"] == "fail"]
    print(f"ZERO-COST SCAN: {'PASS' if not fails else 'FAIL (' + str(len(fails)) + ' issue(s))'}" + "".join(f"\n   {f['severity'].upper()} {f['file']}:{f['line']} {f['message']}" for f in findings))
    if a.json:
        Path(a.json).write_text(json.dumps({"assignment": a.assignment, "score": total, "max": mx, "gate": getattr(mod, "GATE", None) if a.capstone else None, "zero_cost_ok": not fails,
                                            "checks": [dict(vars(r), passed=(r.passed if r.max_points else r.frac >= 0.999)) for r in ctx.results], "scan": findings}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
