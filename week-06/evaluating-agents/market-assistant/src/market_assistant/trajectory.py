from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage


@dataclass
class Step:
    """One tool call made by the agent."""

    tool: str
    args: dict
    observation: str = ""
    error: bool = False
    # unknown_tool | bad_format | bad_args | exec_error, None when the call succeeded
    error_kind: str | None = None
    thought: str = ""


@dataclass
class Trajectory:
    goal: str
    steps: list[Step] = field(default_factory=list)
    final_answer: str = ""

    def tools(self) -> list[str]:
        return [s.tool for s in self.steps]


@dataclass
class RunResult:
    answer: str
    trajectory: Trajectory
    retrieved_context: list[str]  # chunks returned by search_knowledge, for faithfulness judges
    turn: list[BaseMessage] = field(default_factory=list)  # question + final reply; append to history for multi-turn chat
    stopped: bool = False  # True when max_steps was hit and no final answer was produced
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
