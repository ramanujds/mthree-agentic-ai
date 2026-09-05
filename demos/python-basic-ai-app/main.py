import json
import re

from openai import APIError, OpenAI
import argparse
import os
import sys

from pydantic import ValidationError

from tools import TOOLS, tools_prompt_block

DEFAULT_MODEL="docker.io/ai/gemma4:E4B"
DEFAULT_BASE_URL="http://localhost:12434/v1"

SYSTEM_PROMPT = f"""You are a helpful assistant with access to one tool.

{tools_prompt_block()}

To call a tool, reply with ONLY this line (no other text):
ACTION: web_search {{"query": "your search query"}}

If you don't need the tool, just answer the user's question directly in plain text.
Only call the tool when you genuinely need current or external information —
not for things you already know.
"""

MAX_TOOL_RETRIES = 2
MAX_TURNS_KEPT = 12  # Prevent infinite loops if the model keeps calling tools without resolving the user query

ACTION_NAME_PATTERN = re.compile(r"ACTION:\s*(\w+)",re.DOTALL)
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}",re.DOTALL)

def call_model(client: OpenAI, model: str, messages: list[dict]) -> str:
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def try_parse_action(text: str):
    """Extract a tool call from a model reply.

    Returns one of:
    - (None, None)               the model didn't try to call a tool
    - (tool_name, args_dict)     a syntactically valid call
    - (tool_name, raw_str)       the model *tried* to call a tool, but no
                                  parseable JSON object followed — covers
                                  both a truncated call (no closing brace)
                                  and one with broken JSON syntax — distinct
                                  from "no call" so the caller can react.
    """
    name_match = ACTION_NAME_PATTERN.search(text)
    if not name_match:
        return None, None

    tool_name = name_match.group(1)
    remainder = text[name_match.end() :]
    json_match = JSON_OBJECT_PATTERN.search(remainder)
    if not json_match:
        return tool_name, remainder.strip()

    try:
        return tool_name, json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return tool_name, json_match.group(0)

def resolve_tool_call(tool_name: str, raw_args) -> tuple[dict | None, str | None]:
    """Validate and execute one tool call.

    Returns (result, error_message) — exactly one is set. An error is
    handed back to the model as the *exact* validation/lookup problem
    (Note 7 §2/§3), rather than crashing the app or silently guessing.
    """
    if tool_name not in TOOLS:
        # Note 7 §3: suggest, never auto-substitute — the model must confirm
        # a fuzzy match itself rather than the dispatcher silently rerouting it.
        suggestion = get_close_matches(tool_name, TOOLS.keys(), n=1, cutoff=0.6)
        hint = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
        return None, f"Unknown tool '{tool_name}'. Available tools: {list(TOOLS)}.{hint}"

    spec = TOOLS[tool_name]
    if isinstance(raw_args, str):  # JSON failed to parse in try_parse_action
        return None, f"Arguments for '{tool_name}' were not valid JSON: {raw_args}"

    try:
        validated = spec["schema"].model_validate(raw_args)
    except ValidationError as e:
        return None, f"Invalid arguments for '{tool_name}': {e}"

    result = spec["execute"](**validated.model_dump())
    return result, None


def run_turn(client: OpenAI, model: str, messages: list[dict]) -> str:
    """Handle one user turn: at most one tool hop, then a final answer."""
    for _ in range(MAX_TOOL_RETRIES + 1):
        reply = call_model(client, model, messages)
        tool_name, raw_args = try_parse_action(reply)

        if tool_name is None:
            return reply  # model chose to answer directly — no tool needed

        result, error = resolve_tool_call(tool_name, raw_args)
        if error:
            messages.append({"role": "assistant", "content": reply})
            messages.append(
                {"role": "user", "content": f"Tool call failed: {error}. Try again or answer without the tool."}
            )
            continue

        messages.append({"role": "assistant", "content": reply})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Observation from {tool_name}: {json.dumps(result)}\n\n"
                    "Now answer the original question using this observation. Do not call another tool."
                ),
            }
        )
        return call_model(client, model, messages)

    return "I couldn't complete that tool call correctly after a few tries — could you rephrase?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat app with an optional web-search tool.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()

    # Docker Model Runner doesn't check the API key, but the client requires one.
    client = OpenAI(base_url=args.base_url, api_key="not-needed")
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"Chatting with {args.model} (web search enabled) — type 'exit' to leave.\n")
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

        messages.append({"role": "user", "content": user_input})
        try:
            answer = run_turn(client, args.model, messages)
        except APIError as e:
            print(f"[error] {e}. Is Docker Model Runner running? See ../00-local-model-setup/README.md")
            sys.exit(1)

        print(f"Assistant: {answer}\n")
        messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
