#!/usr/bin/env python3
"""Step 2, LangChain variant — the same one-tool chat app as
../02-chat-with-web-search, rebuilt on LangChain's native tool-calling
instead of a hand-rolled text protocol.

The original app teaches the model a strict text format in the system
prompt ("ACTION: web_search {...}") and then regexes that back out of the
reply, because Gemma via Docker Model Runner wasn't assumed to support
provider-native tool-calling reliably. This version tests that assumption:
`ChatOpenAI(...).bind_tools([web_search])` asks the model to return a
structured tool call, and LangChain parses it for you — no ACTION_NAME_PATTERN,
no JSON_OBJECT_PATTERN, no try_parse_action.

Same web_search tool (same DDGS backend, same bounded has_more/total return
shape) as the hand-rolled version, so the only variable being compared is
the tool-calling mechanism itself. Whether this is actually more reliable
than the text-protocol version depends on how well your specific Gemma tag
handles tool-calling through Docker Model Runner's OpenAI-compatible
endpoint — small local models are not guaranteed to honor it every turn.
Run both apps on the same prompts and compare.

Run:
    uv run chat_with_tools.py
"""
import argparse
import os
import sys

from ddgs import DDGS
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import APIError

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/llama3.2:1B-Q8_0")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1")

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a web_search tool. "
    "Only call it when you genuinely need current or external information — "
    "not for things you already know."
)

# Note 7 §7's dispatcher still applies conceptually — we still cap retries
# so a model that keeps mis-calling the tool doesn't loop forever — but the
# *parsing* half of the dispatcher (malformed JSON, hallucinated tool names)
# is now LangChain's problem: bind_tools() validates the call against the
# tool's schema before it ever reaches us.
MAX_TOOL_RETRIES = 2


@tool
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the live web and return up to 5 results (title, url, snippet).

    Use this for anything you can't already answer confidently from general
    knowledge — current events, prices, recent facts.
    """
    with DDGS() as ddgs:
        # Ask for one extra result so we can tell whether more exist,
        # without a second round-trip — same trick as the hand-rolled version.
        hits = list(ddgs.text(query, max_results=max_results + 1))

    has_more = len(hits) > max_results
    hits = hits[:max_results]
    return {
        "results": [{"title": h.get("title"), "url": h.get("href"), "snippet": h.get("body")} for h in hits],
        "has_more": has_more,
        "total": len(hits) + (1 if has_more else 0),
    }


TOOLS = [web_search]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def run_turn(llm_with_tools, messages: list) -> str:
    """Handle one user turn: at most one tool hop, then a final answer.

    This is the entire replacement for the hand-rolled version's
    try_parse_action/resolve_tool_call/run_turn trio: `response.tool_calls`
    arrives already parsed and validated, so there's nothing left to regex.
    """
    for _ in range(MAX_TOOL_RETRIES + 1):
        response = llm_with_tools.invoke(messages)

        if not response.tool_calls:
            return response.content  # model chose to answer directly

        messages.append(response)
        retry_needed = False
        for call in response.tool_calls:
            tool_fn = TOOLS_BY_NAME.get(call["name"])
            if tool_fn is None:
                # Still worth guarding — bind_tools() constrains what the
                # model *should* call, not what a confused model actually
                # emits.
                content = f"Unknown tool '{call['name']}'. Available: {list(TOOLS_BY_NAME)}."
                retry_needed = True
            else:
                try:
                    content = str(tool_fn.invoke(call["args"]))
                except Exception as e:  # tool-side failure, not a parsing failure
                    content = f"Tool '{call['name']}' failed: {e}"
                    retry_needed = True
            messages.append(ToolMessage(content=content, tool_call_id=call["id"]))

        if not retry_needed:
            return llm_with_tools.invoke(messages).content

    return "I couldn't complete that tool call correctly after a few tries — could you rephrase?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat app with an optional web-search tool (LangChain variant).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()

    # Docker Model Runner doesn't check the API key, but the client requires one.
    llm = ChatOpenAI(model=args.model, base_url=args.base_url, api_key="not-needed", temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]

    print(f"Chatting with {args.model} (web search enabled, LangChain tool-calling) — type 'exit' to leave.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if user_input.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        if not user_input:
            continue

        messages.append(HumanMessage(content=user_input))
        try:
            answer = run_turn(llm_with_tools, messages)
        except APIError as e:
            print(f"[error] {e}. Is Docker Model Runner running? See ../00-local-model-setup/README.md")
            sys.exit(1)

        print(f"Assistant: {answer}\n")
        messages.append(AIMessage(content=answer))


if __name__ == "__main__":
    main()
