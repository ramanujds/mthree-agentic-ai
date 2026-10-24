"""Pydantic-AI with NO API key: TestModel (auto-generates schema-valid output) and FunctionModel (you script the 'LLM').
Run:  PYDANTIC_AI_NO_BANNER=1 python examples/pydantic_ai_offline.py"""
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel


class Out(BaseModel):
    answer: str
    fee: float


def fee_tool(kind: str) -> float:
    """Return the fee for a fee type."""
    return {"wire": 15.0}.get(kind, 0.0)


# 1) TestModel: calls your tools and fabricates schema-valid output - perfect for wiring tests
print("TestModel    :", Agent(TestModel(), output_type=Out, tools=[fee_tool]).run_sync("wire fee?").output)


# 2) FunctionModel: a scripted 'LLM' - first request the tool, then return the structured result
def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    last = messages[-1].parts[-1]
    if isinstance(last, ToolReturnPart):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"answer": "The wire fee is 15.", "fee": last.content})])
    return ModelResponse(parts=[ToolCallPart("fee_tool", {"kind": "wire"})])


print("FunctionModel:", Agent(FunctionModel(script), output_type=Out, tools=[fee_tool]).run_sync("wire fee?").output)
