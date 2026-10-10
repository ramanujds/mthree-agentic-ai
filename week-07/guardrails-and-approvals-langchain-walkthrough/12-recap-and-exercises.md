# Step 12 — Recap and Exercises

> Back to index · Previous: Offline Tests

## Quick Reference

| Concept | Where it lives |
|---|---|
| The tools and their scope | `tools.py`, `_find_order` |
| Which tools may run, and how risky each is | `RISK` in `guardrails.py` |
| Amount, count and step limits | `MAX_REFUND`, `MAX_TICKETS_PER_RUN`, `MAX_TOOL_CALLS`, `MAX_ROUNDS` |
| The gate in front of every tool call | `check_tool_call`, returning `allow`, `approve` or `block` |
| Human approval | `ask_human`, called from `run_tool_request` |
| Input gate and masking | `check_input` |
| Warning about planted instructions | `looks_like_injection` |
| Final answer check | `check_output` |
| The soft guardrail | `SYSTEM_PROMPT` |
| Counters and the trace | `RunState` and `RunState.log` |
| Step cap | `for _ in range(g.MAX_ROUNDS)` in `run_agent` |
| Testing without a model | `ScriptedModel` in `test_guardrails.py` |
| Secrets | `.env` (ignored by Git), with `.env.example` as the template |

## Gotchas

| Gotcha | Why it happens |
|---|---|
| The model guesses amounts, even when told not to | A prompt is a request. In testing it asked for 0 and 100 on a 120 order. The amount check and the approval screen are what catch it |
| The model reports something that did not happen | Its final wording is not a record. After a decline, it once explained the refusal with a reason the customer never gave. Read the trace |
| A blocked refund can still be followed by a ticket | That is intended: the block message tells the model to create one. Ticket creation has its own limit |
| A `@tool` function cannot be called like a normal function | It is an object. Use `.invoke({...})` |
| Counters reset on every question | `RunState` is created inside `run_agent`. A real system also limits per user and per day |
| The override-phrase list is easy to get around | Rewording passes it. It is one thin layer, not the defence |
| `get_order_status` hands free text to the model | The delivery note is how the injection gets in. A safer design would not pass outside text to the model at all |
| Changing `RISK` silently removes the approval | The table is the control. Review changes to it like code that moves money |
| With nobody at the keyboard the program declines | `input` raises `EOFError`, and `ask_human` treats that as a no |
| Answers differ on every run | Models choose words with some randomness, and so do their mistakes |

## Discussion Questions

1. Which guardrails in this project are soft and which are hard? What changes if the model is
   swapped for a weaker one?
2. The model asked for a refund of 0 and was blocked. Which layer caught it, and what did the
   block message do for the agent?
3. Why does the approval screen show the order total next to the proposed amount, when the
   model already supplied the amount?
4. Order 4823's delivery note contains a planted instruction. Name three separate things in
   this project that would stop it causing a wrong refund.
5. `must_not_be_asked` makes a test fail if the approver is called. What does that prove that
   `decline_all` cannot?
6. What would you need to change before this could run for many customers at once?

## Exercises

1. Add a fourth order to `ORDERS` for customer C100, then ask about it and about order 5001.
2. Lower `MAX_REFUND` to 100 and refund 120 for order 4821. Watch the block message and the
   agent's recovery.
3. Add `"hand over to a manager"` to `OVERRIDE_PHRASES`, then use it in a question and see the
   input block. Then reword it and see it pass. What does that tell you about the layer?
4. Make `ask_human` also print the customer ID (`CURRENT_CUSTOMER`), so the approver knows
   whose account the refund is for.
5. Add a tool `cancel_order` to `tools.py`. Give it a risk level in `RISK`, decide what
   limits it needs, and write one offline test showing it cannot run without approval.
6. Add a rule to `check_tool_call` that blocks a second `issue_refund` for the same order in
   one question. Add a test that proves it, using a `ScriptedModel` that asks twice.
7. Write the trace to a file, one line per event, so a person can review the day's runs.
   Where is the best place to add it?
8. Give `ask_human` a third choice, "edit", that lets the approver change the amount before
   it runs. What must `run_tool_request` do with the edited value?
9. Rebuild `guardrails.py` from memory in an empty folder, then compare it with the
   reference. Which check did you forget first?

## What's Next

This program wires every guardrail by hand, which is the best way to understand them. Block 4
shows how frameworks such as LangGraph give you the loop, the state and the approval pause as
built-in features, so you can read them with the hand-built version in mind. Lab 2 asks you to
add guardrails and an approval step to your own Lab 1 agent, using the same pattern: sort the
tools by risk, put limits in code, ask a person before anything that is hard to undo, and test
the guardrails with a scripted model.
