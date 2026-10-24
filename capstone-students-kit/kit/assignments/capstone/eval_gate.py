"""CI quality gate. Usage:
    python eval_gate.py reports/eval_after.json --min faithfulness=0.7 --min context_recall=0.8 --max latency_p95_ms=2000 --max sim_cost_usd=0.05
Reads a run_eval() result JSON. Exit code 0 when every threshold holds, 1 when any is violated, 2 on usage/file errors.
Metric names: any key in results["metrics"], plus latency_p50_ms, latency_p95_ms, sim_cost_usd. Print a readable PASS/FAIL line per threshold.
"""
import sys


def main(argv=None) -> int:
    raise NotImplementedError("capstone R4: eval_gate")


if __name__ == "__main__":
    sys.exit(main())
