import ast
import json
import operator
import re
from typing import Literal

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from market_assistant.market import Market, ToolError
from market_assistant.rag import Knowledge

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}


def evaluate_expression(expression: str) -> float:
    """Safely evaluate + - * / ** parentheses and min/max/abs/round. Also reusable by evals to compare tool arguments by value."""
    # drop Indian/US thousands separators (1,25,000 / 38,500) but keep commas between function arguments
    cleaned = re.sub(r"(?<=\d),(?=\d{2,3}(?!\d))", "", expression)
    cleaned = cleaned.replace("Rs.", "").replace("₹", "").strip()

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ToolError("Exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](walk(node.operand))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS
            and not node.keywords
        ):
            return _FUNCS[node.func.id](*[walk(a) for a in node.args])
        raise ToolError(
            f"Unsupported expression: {expression!r}. Use numbers, + - * / **, parentheses, min, max, abs, round"
        )

    try:
        return walk(ast.parse(cleaned, mode="eval"))
    except SyntaxError:
        raise ToolError(f"Could not parse expression: {expression!r}") from None
    except ZeroDivisionError:
        raise ToolError("Division by zero") from None


class CalculatorArgs(BaseModel):
    expression: str = Field(description="Arithmetic expression, e.g. '50 * (2900 - 2500)'")


class QuoteArgs(BaseModel):
    symbol: str = Field(description="NSE ticker symbol, e.g. 'TCS'")


class PortfolioArgs(BaseModel):
    client_id: str = Field(description="Client id, e.g. 'C001'")


class OrderArgs(BaseModel):
    client_id: str = Field(description="Client id, e.g. 'C001'")
    symbol: str = Field(description="NSE ticker symbol, e.g. 'TCS'")
    quantity: int = Field(description="Number of whole shares")
    side: Literal["BUY", "SELL"] = Field(description="BUY or SELL")


class KnowledgeArgs(BaseModel):
    query: str = Field(description="What to look up, e.g. 'brokerage charges' or 'LTCG tax rate'")


def build_tools(market: Market, knowledge: Knowledge, context_log: list[str]) -> list[BaseTool]:
    """`context_log` collects every chunk search_knowledge returns, so evals can see what the agent was shown."""

    @tool("calculator", args_schema=CalculatorArgs)
    def calculator(expression: str) -> str:
        """Evaluate an arithmetic expression exactly. Use it for every calculation (P&L, charges, tax, totals)."""
        value = evaluate_expression(expression)
        return str(int(value)) if float(value).is_integer() else str(round(value, 6))

    @tool("get_quote", args_schema=QuoteArgs)
    def get_quote(symbol: str) -> str:
        """Get the latest traded price, previous close, day high/low, circuit band and market status for an NSE stock."""
        return json.dumps(market.get_quote(symbol))

    @tool("get_portfolio", args_schema=PortfolioArgs)
    def get_portfolio(client_id: str) -> str:
        """Get a client's cash balance and holdings (quantity, average buy price, first buy date, days held)."""
        return json.dumps(market.get_portfolio(client_id))

    @tool("place_order", args_schema=OrderArgs)
    def place_order(client_id: str, symbol: str, quantity: int, side: str) -> str:
        """Place a market delivery order at the last traded price. Changes cash and holdings. Only on an explicit buy/sell request."""
        return json.dumps(market.place_order(client_id, symbol, quantity, side))

    @tool("search_knowledge", args_schema=KnowledgeArgs)
    def search_knowledge(query: str) -> str:
        """Search the market rules knowledge base: trading hours, settlement, circuit limits, brokerage and charges, capital gains tax, order rules."""
        docs = knowledge.search(query)
        context_log.extend(d.page_content for d in docs)
        return "\n\n".join(f"[{d.metadata['source']}]\n{d.page_content}" for d in docs)

    return [calculator, get_quote, get_portfolio, place_order, search_knowledge]
