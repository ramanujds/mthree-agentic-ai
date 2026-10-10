"""Throwaway helper for the walkthrough: one real agent run wrapped as a CaseRun. Delete it at the end."""

from evals.context import CaseRun
from market_assistant import Market, build_agent
from market_assistant.rag import Knowledge

QUESTION = "Buy 5 shares of INFY"

market = Market()
agent = build_agent(client_id="C001", market=market, knowledge=Knowledge())
before = market.snapshot()
result = agent.run(QUESTION)
run = CaseRun({}, "C001", [QUESTION], [result], before, market.snapshot())

if __name__ == "__main__":
    print("answer :", run.answer)
    print("tools  :", run.tools)
    print("orders :", [(o["symbol"], o["side"], o["quantity"]) for o in run.new_orders])
    print("llm calls:", run.llm_calls, " tokens:", run.input_tokens + run.output_tokens)
