"""LlamaIndex Workflows need no LLM at all for routing/orchestration: steps + events are plain async Python.
Run:  python examples/llamaindex_workflow_offline.py"""
import asyncio
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step


class Routed(Event):
    route: str
    text: str


class Router(Workflow):
    @step
    async def route(self, ev: StartEvent) -> Routed:
        return Routed(route="transaction" if "transfer" in ev.text.lower() else "retrieval", text=ev.text)

    @step
    async def handle(self, ev: Routed) -> StopEvent:
        return StopEvent(result=f"[{ev.route}] {ev.text}")


async def main():
    for t in ("What is the wire fee?", "Transfer $500 to BEN-10"):
        print(await Router(timeout=10).run(text=t))


asyncio.run(main())
