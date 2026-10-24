"""Capstone R6 - resilience patterns. No real sleeping in tests: `sleep` and `clock` are injected.

CircuitBreaker(failure_threshold=3, reset_after_s=30.0, clock=time.monotonic)
    .state -> "closed" | "open" | "half_open"      .allow() -> bool      .record_success()      .record_failure()
    closed: counts CONSECUTIVE failures; reaching the threshold opens it (remember when).
    open: allow() is False until reset_after_s has elapsed, then it moves to half_open and allows ONE trial call.
    half_open: success -> closed (counter reset); failure -> open again (restart the timer).

call_with_resilience(fn, *, retries=3, base_delay=0.1, max_delay=2.0, timeout_budget_s=5.0, fallback=None, breaker=None,
                     sleep=time.sleep, clock=time.monotonic, retry_on=(Exception,)) -> dict   (NEVER raises)
    returns {"ok": bool, "value": Any, "attempts": int, "error": None | {"type": str, "message": str}, "used_fallback": bool, "elapsed_s": float}
    * attempts <= 1 + retries; the delay before retry n (n = 1, 2, ...) is min(base_delay * 2**(n-1), max_delay): call sleep(delay)
    * timeout budget: if elapsed + next delay would exceed timeout_budget_s, stop retrying; error.type = "TimeoutBudgetExceeded"
    * exceptions NOT in retry_on are not retried: stop at once; error.type = the exception class name
    * breaker: if given and not breaker.allow() -> do not call fn; attempts=0; error.type = "CircuitOpen". Every failed attempt calls
      breaker.record_failure(), a success calls breaker.record_success()
    * fallback: when the call fails for ANY reason and fallback is not None, value = fallback(), ok=True, used_fallback=True,
      and `error` still describes what went wrong (graceful degradation must stay visible)
    * on plain success: ok=True, error=None, used_fallback=False
"""
from __future__ import annotations
import time


class CircuitBreaker:
    def __init__(self, failure_threshold=3, reset_after_s=30.0, clock=time.monotonic):
        raise NotImplementedError("capstone: implement me")


def call_with_resilience(fn, *, retries=3, base_delay=0.1, max_delay=2.0, timeout_budget_s=5.0, fallback=None, breaker=None,
                         sleep=time.sleep, clock=time.monotonic, retry_on=(Exception,)):
    raise NotImplementedError("capstone: implement me")
