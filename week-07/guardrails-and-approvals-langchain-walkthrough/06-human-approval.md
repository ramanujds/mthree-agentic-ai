# Step 6 — Human Approval

> Back to index · Previous: Permissions and Limits · Next: Input Checks

## Goal

Pause before every high-risk action, show a person exactly what is about to happen, and act on
their answer.

## Why this matters

At the end of Step 5 a refund of 120 went out with nobody asked. It was inside the limit, and
it was probably fine. But "probably fine" is not how you handle money. For actions that are
hard to undo or that leave the building (a refund, an email, a deletion), the agent
**proposes** and a person **decides**. It is the same as a junior colleague who drafts the
letter and brings it to you for a signature.

An approval is only worth something if the approver can read it. A screen that says "perform
an action? yes/no" gets clicked through. So the approval screen shows the exact action, every
input, and **evidence from your own data** (the order total and status), so the person can
spot a wrong amount at a glance. You saw in Step 4 how the model guesses amounts. This screen
is where a person catches them.

Two design choices to keep in mind. A "no" is not a crash: it goes back to the model as a
readable result, so the agent can tell the customer. And if nobody is there to answer, the
safe default is **decline**.

## 1. The Approval Prompt

In `guarded_agent.py`, change the `tools` import so it also brings in `ORDERS`:

```python
from tools import ALL_TOOLS, ORDERS, TOOLS_BY_NAME
```

Then add `ask_human` between the imports and `run_tool_request`:

```python
# ADDED: the human approval step. The agent proposes, a person decides.
def ask_human(name: str, args: dict) -> tuple[bool, str]:
    """Show the exact action and the evidence, then ask. Returns (approved, reason)."""
    print("\n  ----- APPROVAL NEEDED -----")
    print(f"  Action : {name}")
    for key, value in args.items():
        print(f"  {key:<7}: {value}")
    order = ORDERS.get(args.get("order_id", ""))
    if order:
        print(f"  Evidence: order total {order['amount']}, status '{order['status']}'")
    try:
        answer = input("  Approve? [y/N]: ").strip().lower()
        print("  ---------------------------\n")
        if answer in ("y", "yes"):
            return True, ""
        reason = input("  Reason for declining (optional): ").strip()
    except EOFError:
        # Nobody is there to answer. The safe default is to decline.
        return False, "no reviewer was available"
    return False, reason or "no reason given"
```

| Part | What it does |
|---|---|
| The `for` loop | Prints every input the model chose, so nothing is hidden |
| `ORDERS.get(...)` and `Evidence:` | Puts the order total next to the proposed amount, from your data and not the model's |
| `[y/N]` | The capital `N` means the default is no. Anything except `y` or `yes` declines |
| `reason` | Why it was declined, so the model can pass it on |
| `except EOFError` | If input is closed (a script, a test, nobody at the keyboard), decline instead of crashing |

The function returns `(approved, reason)`. It does not know anything about LangChain or the
model. That is why Step 11 can replace it with a fake.

## 2. Use It in the Request Handler

Change the signature of `run_tool_request` so the approver is passed in:

```python
def run_tool_request(call: dict, state: g.RunState, approver) -> str:
```

Then replace the single `allowed` line with a branch on the decision:

```python
    # ADDED: high-risk actions wait for a person.
    if decision.action == "approve":
        approved, reason = approver(name, args)
        if not approved:
            state.log("approval", f"declined ({reason})")
            return f"A human reviewer declined this action (reviewer's note: {reason}). Do not retry it. Tell the customer it was not approved."
        state.log("approval", "approved")
    else:
        state.log("allowed", f"risk level {g.RISK[name]}")
```

Read the decline message closely. It says "reviewer's note", because in testing the model
sometimes mistook the note for the **customer's** reason. It also says "Do not retry it", so
the agent does not ask again and again. Both are small wording choices that change how the
agent behaves.

When the person approves, execution simply continues to the code you already have, which runs
the tool.

## 3. Pass the Approver Down

`run_agent` takes the approver as an argument, with the real prompt as the default:

```python
def run_agent(model_with_tools, question: str, approver=ask_human) -> str:
```

and passes it on in the loop:

```python
            result = run_tool_request(call, state, approver)
```

Making the approver an argument is a design choice. The loop does not care how the decision
is made: a terminal prompt today, a chat message or a ticket queue in a real system, a fake in
the tests.

## Try it

Approve a refund. The `y` is typed at the prompt:

```bash
uv run guarded_agent.py "Refund 120 for order 4821, it arrived damaged"
```

```text
You: Refund 120 for order 4821, it arrived damaged
  [tool request] issue_refund({'order_id': '4821', 'amount': 120, 'reason': 'The item arrived damaged.'})

  ----- APPROVAL NEEDED -----
  Action : issue_refund
  order_id: 4821
  amount : 120
  reason : The item arrived damaged.
  Evidence: order total 120, status 'Shipped, arrives Thursday'
  Approve? [y/N]: y
  ---------------------------

  [approval] approved
  [tool result] Refund RF-0001 issued: 120.0 for order 4821.

AI: A refund of $120 has been issued for order 4821 due to the item arriving damaged.
```

Run it again and answer `n`, then give a reason such as `wrong order number`:

```text
  Approve? [y/N]: n
  ---------------------------

  Reason for declining (optional): wrong order number
  [approval] declined (wrong order number)

AI: I attempted to process the refund of $120 for order 4821, but it was not approved because the order number was incorrect. If you would like me to assist with another order, please provide the correct order number.
```

The refund did not run. Notice that the model paraphrased the note into a story of its own
("the order number was incorrect"). It is a reminder that the model's final wording is not a
record of what happened. The trace is.

Finally, close the input so nobody can answer:

```bash
uv run guarded_agent.py "Refund 120 for order 4821, it arrived damaged" < /dev/null
```

```text
  Approve? [y/N]:   [approval] declined (no reviewer was available)
```

Nothing is refunded. The default is no.

One last experiment. In `guardrails.py`, change `"issue_refund": "high"` to
`"issue_refund": "medium"` and run the first command again. There is no approval screen. The
whole guardrail was one word in a table, so changes to `RISK` deserve a code review. Change it
back.

## Checkpoint

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
from tools import ALL_TOOLS, ORDERS, TOOLS_BY_NAME


# ADDED: the human approval step. The agent proposes, a person decides.
def ask_human(name: str, args: dict) -> tuple[bool, str]:
    """Show the exact action and the evidence, then ask. Returns (approved, reason)."""
    print("\n  ----- APPROVAL NEEDED -----")
    print(f"  Action : {name}")
    for key, value in args.items():
        print(f"  {key:<7}: {value}")
    order = ORDERS.get(args.get("order_id", ""))
    if order:
        print(f"  Evidence: order total {order['amount']}, status '{order['status']}'")
    try:
        answer = input("  Approve? [y/N]: ").strip().lower()
        print("  ---------------------------\n")
        if answer in ("y", "yes"):
            return True, ""
        reason = input("  Reason for declining (optional): ").strip()
    except EOFError:
        # Nobody is there to answer. The safe default is to decline.
        return False, "no reviewer was available"
    return False, reason or "no reason given"


def run_tool_request(call: dict, state: g.RunState, approver) -> str:
    """Apply the guardrails to one tool request and return the text the model will read."""
    name, args = call["name"], call["args"]
    state.log("tool request", f"{name}({args})")

    # ADDED: permission and limit check, in code, before anything runs.
    decision = g.check_tool_call(name, args, state)
    if decision.action == "block":
        state.log("blocked", decision.message)
        return decision.message

    # ADDED: high-risk actions wait for a person.
    if decision.action == "approve":
        approved, reason = approver(name, args)
        if not approved:
            state.log("approval", f"declined ({reason})")
            return f"A human reviewer declined this action (reviewer's note: {reason}). Do not retry it. Tell the customer it was not approved."
        state.log("approval", "approved")
    else:
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


def run_agent(model_with_tools, question: str, approver=ask_human) -> str:
    """One question in, one answer out, with the guardrails around every step."""
    state = g.RunState()

    messages = [HumanMessage(question)]

    while True:
        reply = model_with_tools.invoke(messages)

        if not reply.tool_calls:
            return reply.content

        messages.append(reply)
        for call in reply.tool_calls:
            result = run_tool_request(call, state, approver)
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

This is an intermediate version. `guardrails.py` is unchanged in this step, so it is the same
as the Step 5 checkpoint.

## Common Mistakes

| Symptom | Cause | Fix |
|---|---|---|
| `NameError: ask_human` | `ask_human` is defined below `run_agent`, whose default value needs it at definition time | Define `ask_human` above `run_agent` |
| `TypeError: run_tool_request() missing 1 required positional argument` | You added `approver` to the function but not to the call in the loop | Pass `approver` in `run_tool_request(call, state, approver)` |
| The approval never appears | `issue_refund` is not `"high"` in `RISK`, or the model asked for an amount that was blocked first | Check `RISK`, then check the trace for a `[blocked]` line |
| The program crashes with `EOFError` | The `try`/`except EOFError` is missing | Wrap both `input` calls as shown |
| The prompt looks stuck | It is waiting for you to type at `Approve?` | Type `y` or `n` and press Enter |

Next: **Step 7 — Input Checks**.
