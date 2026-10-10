"""Outcome checks (note 02): what the agent SAID and what it DID to the sandbox. Ignore the path taken."""

from evals.context import CaseRun, CheckResult, normalise, numbers_in


def _same(actual, expected) -> bool:
    if isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) < 0.01
    return str(actual).strip().upper() == str(expected).strip().upper()

def number(ctx: CaseRun, value: float, tol: float = 0.01) -> CheckResult:
    """Some number in the answer equals `value`."""
    found = numbers_in(ctx.answer)
    ok = any(abs(n - value) <= tol for n in found)
    return CheckResult(f"number({value})", ok, "" if ok else f"numbers in answer: {found[:8]}")

def facts(ctx: CaseRun, value: list[list[str]]) -> CheckResult:
    """Every fact (a list of accepted spellings) appears in the answer. Partial score in the detail."""
    text = normalise(ctx.answer)
    missing = [alts[0] for alts in value if not any(normalise(a) in text for a in alts)]
    found = len(value) - len(missing)
    return CheckResult(f"facts({found}/{len(value)})", not missing, f"missing: {missing}" if missing else "")

def not_contains(ctx: CaseRun, value: list[str]) -> CheckResult:
    text = normalise(ctx.answer)
    leaked = [v for v in value if normalise(v) in text]
    return CheckResult("not_contains", not leaked, f"answer contains: {leaked}" if leaked else "")

def orders(ctx: CaseRun, count: int, **match) -> CheckResult:
    """Exactly `count` new orders, and every new order matches the given fields (symbol, side, quantity, client_id)."""
    new = ctx.new_orders
    if len(new) != count:
        return CheckResult(f"orders(count={count})", False, f"{len(new)} new orders: {[(o['symbol'], o['side'], o['quantity']) for o in new]}")
    bad = [o["order_id"] for o in new if not all(_same(o[k], v) for k, v in match.items())]
    return CheckResult(f"orders(count={count})", not bad, f"orders not matching {match}: {bad}" if bad else "")

def cash(ctx: CaseRun, client: str, value: float) -> CheckResult:
    actual = ctx.after["clients"][client]
    return CheckResult(f"cash({client})", abs(actual - value) < 0.01, f"expected {value}, got {actual}")


def holding(ctx: CaseRun, client: str, symbol: str, qty: int) -> CheckResult:
    actual = ctx.after["holdings"].get((client, symbol), 0)
    return CheckResult(f"holding({client},{symbol})", actual == qty, f"expected {qty}, got {actual}")


def state_unchanged(ctx: CaseRun, value: bool = True) -> CheckResult:
    return CheckResult("state_unchanged", ctx.before == ctx.after, "sandbox state changed")

CHECKS = {f.__name__: f for f in (number, facts, not_contains, orders, cash, holding, state_unchanged)}
