"""Shared types: what a checker or judge sees after one case has been run."""

import re
from dataclasses import dataclass, field

from market_assistant import RunResult, Step


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

@dataclass
class CaseRun:
    """One execution of one case (all turns), plus the sandbox state before and after."""

    case: dict
    client_id: str
    turns: list[str]
    results: list[RunResult]
    before: dict  # Market.snapshot()
    after: dict
    latency_s: float = 0.0


    @property
    def answer(self) -> str:
        return self.results[-1].answer

    @property
    def steps(self) -> list[Step]:
        return [s for r in self.results for s in r.trajectory.steps]

    @property
    def tools(self) -> list[str]:
        return [s.tool for s in self.steps]

    @property
    def stopped(self) -> bool:
        return any(r.stopped for r in self.results)

    @property
    def new_orders(self) -> list[dict]:
        return self.after["orders"][len(self.before["orders"]) :]

    @property
    def llm_calls(self) -> int:
        return sum(r.llm_calls for r in self.results)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.results)

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.results)

def numbers_in(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def normalise(text: str) -> str:
    """Lowercase and drop thousands separators so '1,25,000' matches '125000'."""
    return re.sub(r"\s+", " ", text.lower().replace(",", "")).strip()
