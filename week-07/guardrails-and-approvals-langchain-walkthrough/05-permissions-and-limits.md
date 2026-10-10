# Step 5 — Permissions and Limits

> Back to index · Previous: A Plain Agent Loop · Next: Human Approval

## Goal

Create `guardrails.py` with a risk table and limits, and put a check between "the model asked"
and "the function ran".

## Why this matters

In Step 4 the model's request went straight to the function. Now you add the gate. It answers
three questions in code, every time:

1. Is this tool on the list of tools the agent may use at all?
2. Is the request inside the limits (how much, how many)?
3. How risky is it, and so what should happen: run, ask a person, or refuse?

This is **least privilege**: the agent gets only the access the job needs. If the model is
fooled or just confused, the damage is capped by what the gate allows. An agent that cannot
refund more than 500 cannot refund 900, however politely or cleverly it is asked.

A blocked request is not an error. The agent receives a readable sentence ("Refunds above
500 are not allowed here. Create a support ticket...") and can act on it. In the Try it
below the model reads that sentence and creates a ticket by itself.

## 1. The File Header and Settings

Create `guardrails.py`:

```python
"""The guardrails: plain Python rules that sit around the model.

Nothing in this file calls an LLM or LangChain. That is the point: these are hard
guardrails, enforced in code, so the model cannot talk its way past them. They can
be tested on their own (see test_guardrails.py).
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Settings. Change these to see the guardrails react.
# ---------------------------------------------------------------------------

MAX_TOOL_CALLS = 6  # tool requests per question
MAX_TICKETS_PER_RUN = 2  # count limit on a medium-risk tool
MAX_REFUND = 500  # amount limit: anything above is blocked outright
```

| Setting | The limit it sets |
|---|---|
| `MAX_TOOL_CALLS` | How many tools may run for one question, so a runaway agent stops |
| `MAX_TICKETS_PER_RUN` | A count limit on the medium-risk tool |
| `MAX_REFUND` | An amount limit on the high-risk tool |

Notice that nothing in this file imports LangChain. Pure Python rules can be tested without a
model, which is exactly what Step 11 does.

## 2. The Risk Table

```python
# Permissions: every tool the agent may use, sorted by risk. A tool that is not
# listed here does not run, whatever the model asks for.
RISK = {
    "get_order_status": "low",  # read only: allow and log
    "create_support_ticket": "medium",  # reversible action: allow within a limit
    "issue_refund": "high",  # hard to undo: ask a human first
}
```

This table does two jobs. It is the **allow list**: a name that is not a key is not a tool.
And it is the **risk sort** from Step 1, with the default control in each comment. When you
add a fourth tool later, you must decide its level here before it can run at all.

## 3. Run State and Decisions

```python
@dataclass
class RunState:
    """What has happened so far in one question. Counters live here, not in the model."""

    tool_calls: int = 0
    tickets: int = 0
    events: list = field(default_factory=list)  # the trace of the run

    def log(self, tag: str, message: str) -> None:
        self.events.append((tag, message))
        print(f"  [{tag}] {message}")


@dataclass
class Decision:
    """The verdict on one tool request: allow, approve (ask a human) or block."""

    action: str
    message: str = ""
```

`RunState` holds the counters for one question. They live in your code, not in the model's
memory, because a model can lose count or be talked into forgetting. `log` is the **trace**:
it prints a tagged line such as `[blocked]` or `[allowed]` and also keeps it in `events`.
Nothing the guardrails do should be invisible.

`Decision` is the answer the gate gives: `allow`, `approve` (ask a person) or `block`, with a
message for the model when blocking.

## 4. The Gate

```python
# ---------------------------------------------------------------------------
# Layer 2: tool permissions and limits
# ---------------------------------------------------------------------------


def check_tool_call(name: str, args: dict, state: RunState) -> Decision:
    """Decide what happens to one tool request: allow, approve or block."""
    risk = RISK.get(name)
    if risk is None:
        return Decision("block", f"The tool '{name}' is not available.")

    if state.tool_calls >= MAX_TOOL_CALLS:
        return Decision("block", f"Tool limit reached ({MAX_TOOL_CALLS} per question). Stop and answer with what you have.")

    # Tool-specific limits.
    if name == "issue_refund":
        amount = args.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            return Decision("block", "The refund amount must be a number above zero.")
        if amount > MAX_REFUND:
            return Decision(
                "block",
                f"Refunds above {MAX_REFUND} are not allowed here. "
                "Create a support ticket so a manager can review it.",
            )
    if name == "create_support_ticket" and state.tickets >= MAX_TICKETS_PER_RUN:
        return Decision("block", f"Ticket limit reached ({MAX_TICKETS_PER_RUN} per question).")

    # Risk decides the default control.
    if risk == "high":
        return Decision("approve")
    return Decision("allow")
```

The checks run in order, cheapest and most basic first:

| Check | Blocks when | Why it is there |
|---|---|---|
| Unknown tool | The name is not in `RISK` | The model can invent or be told to call tools that do not exist |
| Tool-call cap | `MAX_TOOL_CALLS` already reached | Stops a loop from calling tools forever |
| Refund amount | Zero, negative, not a number, or above `MAX_REFUND` | The model often guesses amounts. Zero is a common guess |
| Ticket cap | `MAX_TICKETS_PER_RUN` already reached | Stops the same ticket being raised again and again |
| Risk level | (not a block) a `high` tool returns `approve` | Hands the decision to a person in Step 6 |

Every block message tells the model **what to do instead**. A message that only says "no"
leaves the agent stuck. A message that says "create a ticket" lets it recover.

## 5. Wire the Gate Into the Agent

In `guarded_agent.py`, add the import below the LangChain imports:

```python
import guardrails as g
from tools import ALL_TOOLS, TOOLS_BY_NAME
```

Then replace the body of the loop with a function of its own. Add `run_tool_request` above
`run_agent`:

```python
def run_tool_request(call: dict, state: g.RunState) -> str:
    """Apply the guardrails to one tool request and return the text the model will read."""
    name, args = call["name"], call["args"]
    state.log("tool request", f"{name}({args})")

    # ADDED: permission and limit check, in code, before anything runs.
    decision = g.check_tool_call(name, args, state)
    if decision.action == "block":
        state.log("blocked", decision.message)
        return decision.message

    state.log("allowed", f"risk level {g.RISK[name]}")

    # Run the real function. A failure becomes readable text, not a crash.
    state.tool_calls += 1
    try:
        result = TOOLS_BY_NAME[name].invoke(args)
    except Exception as error:
        state.log("tool error", str(error))
        return f"The tool failed: {error}"
    if name == "create_support_ticket":
        state.tickets += 1

    state.log("tool result", result)
    return result
```

Three details worth pointing out:

- A blocked request returns **before** the function runs. The message goes to the model
  exactly as a tool result would.
- The counters (`state.tool_calls`, `state.tickets`) go up only after a call is allowed, so
  blocked calls do not use up the budget.
- The `try`/`except` turns a crash inside a tool into a sentence. A bad input or a failing
  service becomes something the model can react to.

For now a `high` risk request is treated like the others: `check_tool_call` says `approve`,
but nothing asks yet. That is Step 6.

Now update `run_agent` to create the state and call the new function:

```python
def run_agent(model_with_tools, question: str) -> str:
    """One question in, one answer out, with the guardrails around every step."""
    state = g.RunState()

    messages = [HumanMessage(question)]

    while True:
        reply = model_with_tools.invoke(messages)

        if not reply.tool_calls:
            return reply.content

        messages.append(reply)
        for call in reply.tool_calls:
            result = run_tool_request(call, state)
            messages.append(ToolMessage(result, tool_call_id=call["id"]))
```

## Try it

First, the gate on its own, with no model:

```bash
uv run python -c "
import guardrails as g
s = g.RunState()
print(g.check_tool_call('issue_refund', {'amount': 900}, s))
print(g.check_tool_call('issue_refund', {'amount': 120}, s))
print(g.check_tool_call('get_order_status', {}, s))
print(g.check_tool_call('delete_everything', {}, s))
"
```

```text
Decision(action='block', message='Refunds above 500 are not allowed here. Create a support ticket so a manager can review it.')
Decision(action='approve', message='')
Decision(action='allow', message='')
Decision(action='block', message="The tool 'delete_everything' is not available.")
```

Now with the model. Give it an amount, so it cannot guess:

```bash
uv run guarded_agent.py "Refund 900 for order 4823"
```

```text
You: Refund 900 for order 4823
  [tool request] issue_refund({'order_id': '4823', 'amount': 900, 'reason': 'Customer requested a refund.'})
  [blocked] Refunds above 500 are not allowed here. Create a support ticket so a manager can review it.
  [tool request] create_support_ticket({'order_id': '4823', 'summary': 'Customer requested a refund of 900 for order 4823.'})
  [allowed] risk level medium
  [tool result] Ticket T-1001 created for order 4823. A person will follow up.

AI: I've created a support ticket (Ticket T-1001) for your refund request of $900 for order 4823. A representative will follow up with you soon.
```

The limit held, and the agent recovered by following the advice in the block message. Now a
refund inside the limit:

```bash
uv run guarded_agent.py "Refund 120 for order 4821, it arrived damaged"
```

```text
You: Refund 120 for order 4821, it arrived damaged
  [tool request] issue_refund({'order_id': '4821', 'amount': 120, 'reason': 'The item arrived damaged.'})
  [allowed] risk level high
  [tool result] Refund RF-0001 issued: 120.0 for order 4821.

AI: A refund of $120 has been issued for order 4821, due to the item arriving damaged.
```

Money moved and nobody was asked. The trace even says `risk level high`, and still it ran.
A limit stops the biggest mistakes, but not the ones just below it. That gap is why the
high-risk tool needs a person, and it is the next step.

## Checkpoint

<details>
<summary>Full <code>guardrails.py</code> after this step</summary>

```python
"""The guardrails: plain Python rules that sit around the model.

Nothing in this file calls an LLM or LangChain. That is the point: these are hard
guardrails, enforced in code, so the model cannot talk its way past them. They can
be tested on their own (see test_guardrails.py).
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Settings. Change these to see the guardrails react.
# ---------------------------------------------------------------------------

MAX_TOOL_CALLS = 6  # tool requests per question
MAX_TICKETS_PER_RUN = 2  # count limit on a medium-risk tool
MAX_REFUND = 500  # amount limit: anything above is blocked outright

# Permissions: every tool the agent may use, sorted by risk. A tool that is not
# listed here does not run, whatever the model asks for.
RISK = {
    "get_order_status": "low",  # read only: allow and log
    "create_support_ticket": "medium",  # reversible action: allow within a limit
    "issue_refund": "high",  # hard to undo: ask a human first
}


@dataclass
class RunState:
    """What has happened so far in one question. Counters live here, not in the model."""

    tool_calls: int = 0
    tickets: int = 0
    events: list = field(default_factory=list)  # the trace of the run

    def log(self, tag: str, message: str) -> None:
        self.events.append((tag, message))
        print(f"  [{tag}] {message}")


@dataclass
class Decision:
    """The verdict on one tool request: allow, approve (ask a human) or block."""

    action: str
    message: str = ""


# ---------------------------------------------------------------------------
# Layer 2: tool permissions and limits
# ---------------------------------------------------------------------------


def check_tool_call(name: str, args: dict, state: RunState) -> Decision:
    """Decide what happens to one tool request: allow, approve or block."""
    risk = RISK.get(name)
    if risk is None:
        return Decision("block", f"The tool '{name}' is not available.")

    if state.tool_calls >= MAX_TOOL_CALLS:
        return Decision("block", f"Tool limit reached ({MAX_TOOL_CALLS} per question). Stop and answer with what you have.")

    # Tool-specific limits.
    if name == "issue_refund":
        amount = args.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            return Decision("block", "The refund amount must be a number above zero.")
        if amount > MAX_REFUND:
            return Decision(
                "block",
                f"Refunds above {MAX_REFUND} are not allowed here. "
                "Create a support ticket so a manager can review it.",
            )
    if name == "create_support_ticket" and state.tickets >= MAX_TICKETS_PER_RUN:
        return Decision("block", f"Ticket limit reached ({MAX_TICKETS_PER_RUN} per question).")

    # Risk decides the default control.
    if risk == "high":
        return Decision("approve")
    return Decision("allow")
```

</details>

<details>
<summary>Full <code>guarded_agent.py</code> after this step</summary>

```python
"""An order assistant with guardrails and a human approval step.

Built on simple-tool-calling-langchain. The tool-calling loop is the same; every line
that adds a guardrail is marked with an ADDED comment.
"""

import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

import guardrails as g
from tools import ALL_TOOLS, TOOLS_BY_NAME


def run_tool_request(call: dict, state: g.RunState) -> str:
    """Apply the guardrails to one tool request and return the text the model will read."""
    name, args = call["name"], call["args"]
    state.log("tool request", f"{name}({args})")

    # ADDED: permission and limit check, in code, before anything runs.
    decision = g.check_tool_call(name, args, state)
    if decision.action == "block":
        state.log("blocked", decision.message)
        return decision.message

    state.log("allowed", f"risk level {g.RISK[name]}")

    # Run the real function. A failure becomes readable text, not a crash.
    state.tool_calls += 1
    try:
        result = TOOLS_BY_NAME[name].invoke(args)
    except Exception as error:
        state.log("tool error", str(error))
        return f"The tool failed: {error}"
    if name == "create_support_ticket":
        state.tickets += 1

    state.log("tool result", result)
    return result


def run_agent(model_with_tools, question: str) -> str:
    """One question in, one answer out, with the guardrails around every step."""
    state = g.RunState()

    messages = [HumanMessage(question)]

    while True:
        reply = model_with_tools.invoke(messages)

        if not reply.tool_calls:
            return reply.content

        messages.append(reply)
        for call in reply.tool_calls:
            result = run_tool_request(call, state)
            messages.append(ToolMessage(result, tool_call_id=call["id"]))


def main() -> None:
    load_dotenv()
    model = ChatOpenAI(model="gpt-4o-mini")
    model_with_tools = model.bind_tools(ALL_TOOLS)

    # A question on the command line runs once. Otherwise chat until a blank line.
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print("You:", question)
        print("\nAI:", run_agent(model_with_tools, question))
        return

    print("Order assistant. Type a question, or press Enter on a blank line to quit.")
    while question := input("\nYou: ").strip():
        print("\nAI:", run_agent(model_with_tools, question))


if __name__ == "__main__":
    main()
```

</details>

These are intermediate versions. They do not match the reference yet.

## Common Mistakes

| Symptom | Cause | Fix |
|---|---|---|
| `AttributeError: module 'guardrails' has no attribute ...` | A typo in a setting name, or the file was not saved | Compare the names with the checkpoint, and save the file |
| Every refund is blocked | `MAX_REFUND` is lower than the amounts you are testing | Check the setting. Order 4821 has a total of 120 |
| The model asks for a refund of 0 and gets blocked | It guessed an amount. This is the model, not your code | The block is correct. Step 8 reduces how often it happens |
| A blocked call still increases the tool counter | `state.tool_calls += 1` was placed above the block check | Keep the counters after the block check, as shown |

Next: **Step 6 — Human Approval**.
