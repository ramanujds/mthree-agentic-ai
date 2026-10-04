"""A small ReAct agent. llama3:8b has no native tool calling in Ollama, so the loop is prompt based.

Each model turn is one JSON step, enforced with Ollama's structured output so the format cannot break:

    {"thought": ..., "action": "<tool>" | "final_answer", "action_input": {...}, "final_answer": ""}

The loop runs the tool, appends "Observation: ..." and asks for the next step, until final_answer.
"""

import json

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from market_assistant import config
from market_assistant.market import AS_OF, Market, ToolError
from market_assistant.rag import Knowledge
from market_assistant.tools import build_tools
from market_assistant.trajectory import RunResult, Step, Trajectory

SYSTEM_PROMPT = """You are a stock market assistant for retail investors in India (NSE shares), working in a paper-trading sandbox. Today's date is {today}. The logged-in client is {client_id}.

You can use these tools:
{tool_docs}

Respond ONLY with one JSON object per turn, with these keys:
{{"thought": "<what you need to do next and why>", "action": "<tool name, or final_answer>", "action_input": {{<tool arguments>}}, "final_answer": ""}}

- To use a tool: set "action" to the tool name, "action_input" to its arguments and leave "final_answer" empty. The system replies with "Observation: ...", then you take the next step.
- When you have everything the client asked for: set "action" to "final_answer", "action_input" to {{}} and write your reply in "final_answer".

Rules:
0. Answer only what the client asked, using as few tool calls as possible. As soon as you have the information, give the final answer. Never take an action the client did not ask for.
1. Never do arithmetic yourself. Always use the calculator tool.
2. Prices come only from get_quote. Cash and holdings come only from get_portfolio. Never guess them.
3. Market rules, charges, taxes and timings come only from search_knowledge. Do not answer them from memory. If the knowledge base does not contain the answer, say you do not have that information.
4. Only use data for the logged-in client {client_id}.
5. Call place_order ONLY when the client explicitly asks to buy or sell. Before it, check get_portfolio and get_quote. Place at most one order per request. If place_order fails, do NOT retry it: tell the client what happened.
6. If a tool returns an error caused by your input, fix the input. Otherwise report the error honestly.
7. Do not predict prices or give investment advice. For tax and investment topics, add that this is general information, not advice.
8. Keep the final answer short and show amounts in Rs.

Example (sample numbers):
Question: What is ITC trading at?
{{"thought": "I need the latest price of ITC.", "action": "get_quote", "action_input": {{"symbol": "ITC"}}, "final_answer": ""}}
Observation: {{"symbol": "ITC", "ltp": 100.0, "market_status": "OPEN"}}
{{"thought": "I have the price, so I can answer.", "action": "final_answer", "action_input": {{}}, "final_answer": "ITC is trading at Rs. 100.00."}}"""

NEXT_HINT = "Reply with the next JSON step, or action final_answer if you already have everything the client asked for."


def describe_tool(tool: BaseTool) -> str:
    props = tool.args_schema.model_json_schema().get("properties", {})
    sig = []
    notes = []
    for name, p in props.items():
        typ = " | ".join(f'"{v}"' for v in p["enum"]) if "enum" in p else p.get("type", "any")
        sig.append(f"{name}: {typ}")
        notes.append(f"    {name}: {p.get('description', '')}")
    return f"- {tool.name}({', '.join(sig)}): {tool.description}\n" + "\n".join(notes)


def parse_reply(text: str) -> tuple[str, dict]:
    """Returns (kind, data). kind is 'final', 'action' or 'invalid'."""
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return "invalid", {"error": "Reply must be a single JSON object with thought, action, action_input, final_answer"}

    thought = str(data.get("thought", "")).strip()
    action = str(data.get("action", "")).strip()
    if action == "final_answer":
        answer = str(data.get("final_answer", "")).strip()
        if not answer:
            return "invalid", {"error": "action final_answer needs a non-empty final_answer"}
        return "final", {"answer": answer, "thought": thought}
    args = data.get("action_input")
    return "action", {"tool": action, "args": args if isinstance(args, dict) else {}, "thought": thought}


class MarketAssistant:
    def __init__(
        self,
        llm: ChatOllama,
        market: Market,
        knowledge: Knowledge,
        client_id: str = "C001",
        max_steps: int = config.MAX_STEPS,
        verbose: bool = False,
    ):
        self.llm = llm
        self.market = market
        self.client_id = client_id
        self.max_steps = max_steps
        self.verbose = verbose
        self._context_log: list[str] = []
        # name -> tool. Replace an entry to inject faults, e.g. agent.tools["place_order"] = failing_tool
        self.tools: dict[str, BaseTool] = {t.name: t for t in build_tools(market, knowledge, self._context_log)}
        self.response_schema = {
            "type": "object",
            "properties": {
                "thought": {"type": "string"},
                "action": {"type": "string", "enum": [*self.tools, "final_answer"]},
                "action_input": {"type": "object"},
                "final_answer": {"type": "string"},
            },
            "required": ["thought", "action", "action_input", "final_answer"],
        }
        self.system_prompt = SYSTEM_PROMPT.format(
            today=AS_OF.isoformat(),
            client_id=client_id,
            tool_docs="\n".join(describe_tool(t) for t in self.tools.values()),
        )

    def run(self, goal: str, history: list[BaseMessage] | None = None) -> RunResult:
        self._context_log.clear()
        messages: list[BaseMessage] = [
            SystemMessage(self.system_prompt),
            *(history or []),
            HumanMessage(f"Question: {goal}"),
        ]
        traj = Trajectory(goal=goal)
        result = RunResult(answer="", trajectory=traj, retrieved_context=[])

        for _ in range(self.max_steps):
            ai = self.llm.invoke(messages, format=self.response_schema)
            result.llm_calls += 1
            usage = ai.usage_metadata or {}
            result.input_tokens += usage.get("input_tokens", 0)
            result.output_tokens += usage.get("output_tokens", 0)

            kind, data = parse_reply(str(ai.content))
            if kind == "final":
                traj.final_answer = result.answer = data["answer"]
                result.turn = [HumanMessage(f"Question: {goal}"), ai]
                self._log("final", data["answer"])
                break

            if kind == "invalid":
                step = Step(
                    tool="<unparsed>",
                    args={},
                    observation=f"ERROR: {data['error']}",
                    error=True,
                    error_kind="bad_format",
                )
            else:
                step = self._execute(data["tool"], data["args"], data["thought"])
            traj.steps.append(step)
            self._log("step", step)
            messages += [ai, HumanMessage(f"Observation: {step.observation}\n\n{NEXT_HINT}")]
        else:
            result.stopped = True
            traj.final_answer = result.answer = f"Stopped: exceeded max_steps ({self.max_steps})"
            result.turn = [HumanMessage(f"Question: {goal}"), AIMessage(result.answer)]

        result.retrieved_context = list(self._context_log)
        return result

    def _execute(self, name: str, args: dict, thought: str) -> Step:
        step = Step(tool=name, args=args, thought=thought)
        tool = self.tools.get(name)
        if tool is None:
            step.observation = f"ERROR: unknown tool '{name}'. Available tools: {', '.join(self.tools)}"
            step.error, step.error_kind = True, "unknown_tool"
            return step
        try:
            step.observation = str(tool.invoke(args))
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
            step.observation = f"ERROR: invalid arguments for {name}: {problems}"
            step.error, step.error_kind = True, "bad_args"
        except ToolError as e:
            step.observation = f"ERROR: {e}"
            step.error, step.error_kind = True, "exec_error"
        except Exception as e:  # noqa: BLE001 - any tool failure becomes an observation, like a real agent runtime
            step.observation = f"ERROR: {type(e).__name__}: {e}"
            step.error, step.error_kind = True, "exec_error"
        return step

    def _log(self, kind: str, payload) -> None:
        if not self.verbose:
            return
        if kind == "step":
            print(f"  Thought: {payload.thought}\n  Action: {payload.tool} {json.dumps(payload.args)}")
            print(f"  Observation: {payload.observation[:300]}")
        else:
            print(f"  Final Answer: {payload}")


def build_agent(
    client_id: str = "C001",
    market: Market | None = None,
    knowledge: Knowledge | None = None,
    model: str = config.LLM_MODEL,
    verbose: bool = False,
    max_steps: int = config.MAX_STEPS,
    temperature: float = 0.0,
    seed: int = 42,
) -> MarketAssistant:
    """Pass a shared `knowledge` and a fresh `market` per run when evaluating: indexing is slow, sandbox state is not shareable."""
    llm = ChatOllama(
        model=model,
        base_url=config.OLLAMA_BASE_URL,
        temperature=temperature,
        seed=seed,
        num_ctx=8192,
    )
    return MarketAssistant(
        llm=llm,
        market=market or Market(),
        knowledge=knowledge or Knowledge(),
        client_id=client_id,
        max_steps=max_steps,
        verbose=verbose,
    )
