# Step 4 — A Plain Agent Loop

> Back to index · Previous: Write the Tools · Next: Permissions and Limits

## Goal

Build the tool-calling loop with no guardrails at all, and run it to see exactly what goes
wrong.

## Why this matters

Guardrails are easy to nod along to and hard to feel. This step is the "before" picture. You
will write the shortest loop that works, give the model all three tools, and watch it spend
money on a guess.

The loop is the one from the simple-tool-calling walkthrough, written with LangChain:
`bind_tools` hands the tools to the model once, `invoke` sends the messages, a `ToolMessage`
carries each result back. The `simple-tool-calling-langchain` README has a table of what
changed from the plain SDK. What is new here is that the loop repeats until the model stops
asking for tools, which is what makes it an agent.

It is written as `while True` on purpose. A loop with no limit is the second thing you will
fix.

## 1. The Imports

Create `guarded_agent.py`:

```python
"""An order assistant with guardrails and a human approval step.

Built on simple-tool-calling-langchain. The tool-calling loop is the same; every line
that adds a guardrail is marked with an ADDED comment.
"""

import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from tools import ALL_TOOLS, TOOLS_BY_NAME
```

Only `HumanMessage` and `ToolMessage` for now. The system message and the other imports
arrive with the steps that need them.

## 2. The Loop

```python
def run_agent(model_with_tools, question: str) -> str:
    """One question in, one answer out. No guardrails yet."""
    messages = [HumanMessage(question)]

    while True:
        reply = model_with_tools.invoke(messages)

        if not reply.tool_calls:
            return reply.content

        messages.append(reply)
        for call in reply.tool_calls:
            print(f"  [tool request] {call['name']}({call['args']})")
            result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
            print(f"  [tool result] {result}")
            messages.append(ToolMessage(result, tool_call_id=call["id"]))
```

| Line | What it does |
|---|---|
| `model_with_tools` | A model that has been given the tool list. Passed in, so tests can later swap in a fake |
| `if not reply.tool_calls` | No tool request means the model has its answer, so return it |
| `messages.append(reply)` | The model's request goes into the conversation before its result |
| `TOOLS_BY_NAME[call["name"]].invoke(call["args"])` | Your code runs the real function. The model only asked |
| `ToolMessage(..., tool_call_id=call["id"])` | Tags the result with the id of the request it answers |

Read the middle of the `for` loop again. The model's request is run **as asked**, with no
check of any kind between "the model said so" and "the function ran". Every later step is
about that gap.

## 3. The Command Line

```python
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

`bind_tools` is called once. Either a question on the command line (run once, handy for
demos) or a chat that ends at a blank line. This `main` does not change again.

## Try it

A harmless question first:

```bash
uv run guarded_agent.py "Where is my order 4821?"
```

```text
You: Where is my order 4821?
  [tool request] get_order_status({'order_id': '4821'})
  [tool result] Order 4821: Shipped, arrives Thursday. Order total: 120.

AI: Your order 4821 has been shipped and is expected to arrive on Thursday. The total for your order is $120.
```

Now the one that matters:

```bash
uv run guarded_agent.py "Refund order 4823 in full"
```

```text
You: Refund order 4823 in full
  [tool request] issue_refund({'order_id': '4823', 'amount': 100, 'reason': 'Customer requested a full refund.'})
  [tool result] Refund RF-0001 issued: 100.0 for order 4823.

AI: A full refund of $100 has been issued for order 4823. If you need any further assistance, feel free to ask!
```

Look at what happened. Nobody was asked. The order total is 900, but the model invented an
amount of 100, paid it, and then told the customer it was a "full refund". Your wording
will differ and the invented amount may vary, but the pattern is the point: the model acted
confidently on a guess, and the program let it. Also try:

```bash
uv run guarded_agent.py "Where is my order 4823?"
```

The delivery note will appear in the tool result, instruction and all. This time the model
usually ignores it, but nothing in your code made sure of that.

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

from tools import ALL_TOOLS, TOOLS_BY_NAME


def run_agent(model_with_tools, question: str) -> str:
    """One question in, one answer out. No guardrails yet."""
    messages = [HumanMessage(question)]

    while True:
        reply = model_with_tools.invoke(messages)

        if not reply.tool_calls:
            return reply.content

        messages.append(reply)
        for call in reply.tool_calls:
            print(f"  [tool request] {call['name']}({call['args']})")
            result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
            print(f"  [tool result] {result}")
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

This is an intermediate version. It has no guardrails and does not match the reference yet.

## Common Mistakes

| Symptom | Cause | Fix |
|---|---|---|
| `openai.AuthenticationError` (a 401) | The key is missing, wrong, or `.env` is not in the folder you ran from | Check `.env` for `OPENAI_API_KEY=` and run from the project folder |
| `ModuleNotFoundError: tools` | You ran the script from a different folder | `cd` into the project folder, then `uv run guarded_agent.py` |
| A 400 error mentioning `tool_call_id` | The model's request was not added to `messages` before the result, or the id does not match | Keep `messages.append(reply)` before the `for` loop, and pass `call["id"]` |
| The program never stops | The model keeps asking for tools and `while True` has no limit | Nothing yet. Step 10 adds the limit |
| The answer mentions `$` | The model added a currency symbol. The data has no currency | Ignore it. Models add detail you did not give them |

Next: **Step 5 — Permissions and Limits**.
