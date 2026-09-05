"""Tool definitions for the tool-augmented chat app.

Per Week 2 Note 5 §7, a tool is a contract: a name, a typed argument schema,
and a predictable return shape — not just "a Python function the model
happens to call". We use Pydantic for the schema (Note 3 §2) so a malformed
call can be rejected *before* it runs, and we design the return shape to
never lie about being complete (Note 7 §4).
"""
from pydantic import BaseModel, Field
from ddgs import DDGS


class WebSearchArgs(BaseModel):
    """Arguments for the web_search tool. Extra/misspelled fields from the
    model are rejected by Pydantic rather than silently ignored."""

    query: str = Field(..., description="The search query, e.g. 'current weather in Tokyo'")


def web_search(query: str, max_results: int = 5) -> dict:
    """Run a live web search and return a small, bounded set of results.

    Returns an explicit `has_more`/`total` shape (Note 7 §4) instead of a
    bare list — the caller (and the model) should never mistake "top 5
    shown" for "the complete picture" the way a bare list implies.
    """
    with DDGS() as ddgs:
        # Ask for one extra result so we can tell whether more exist,
        # without a second round-trip.
        hits = list(ddgs.text(query, max_results=max_results + 1))

    has_more = len(hits) > max_results
    hits = hits[:max_results]
    return {
        "results": [{"title": h.get("title"), "url": h.get("href"), "snippet": h.get("body")} for h in hits],
        "has_more": has_more,
        "total": len(hits) + (1 if has_more else 0),
    }


# The tool registry: everything the dispatcher needs to validate, describe,
# and execute a call, keyed by the name the model uses in its ACTION line.
TOOLS = {
    "web_search": {
        "schema": WebSearchArgs,
        "execute": web_search,
        "description": (
            "Search the live web and return up to 5 results (title, url, snippet). "
            "Use it for anything you can't already answer confidently from general "
            "knowledge — current events, prices, recent facts."
        ),
    }
}


def tools_prompt_block() -> str:
    """Render the tool contract as text for the system prompt.

    Small local models served via Docker Model Runner (Gemma included) don't
    reliably support the provider-native "tools" API parameter the way
    hosted Claude/GPT calls do. So instead of relying on that, we teach the
    model a strict text protocol by hand — the same underlying idea (name +
    typed args script), just carried in the prompt instead of an API field.
    """
    lines = ["Available tools:"]
    for name, spec in TOOLS.items():
        field_names = ", ".join(spec["schema"].model_fields)
        lines.append(f"- {name}({field_names}): {spec['description']}")
    return "\n".join(lines)
