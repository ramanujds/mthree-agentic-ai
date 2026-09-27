"""Custom CrewAI tool for the Shopping Organizer agent.

`llama3:8b` can't reliably do the category-subtotal/total arithmetic itself
(small local models are shaky at multi-step arithmetic), so the tool does
all of the math in plain Python and hands back JSON that already matches
the `ShoppingPlan` schema almost verbatim. The agent's job is just to
gather the ingredient list and make one tool call -- not to compute totals.
"""

import json
from collections import defaultdict

from crewai.tools import tool

from price_catalog import lookup_category, lookup_price


@tool("price_lookup")
def price_lookup(items: list[str]) -> str:
    """Given a list of grocery ingredient descriptions (e.g. "2 lbs chicken
    breast"), look up each item's estimated USD price and store category,
    group them by category with subtotals, and compute the grand total
    cost. Returns JSON shaped like:
    {"categories": [{"category": str, "items": [{"name": str, "quantity": "",
    "estimated_price": float, "category": str}], "subtotal": float}],
    "total_cost": float}

    Call it ONCE with every ingredient at once, e.g.:
    Action Input: {"items": ["2 lbs chicken breast", "1 cup rice", "1 onion"]}
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        price = lookup_price(item)
        category = lookup_category(item)
        grouped[category].append(
            {"name": item, "quantity": "", "estimated_price": price, "category": category}
        )

    categories = []
    total_cost = 0.0
    for category, priced_items in sorted(grouped.items()):
        subtotal = round(sum(p["estimated_price"] for p in priced_items), 2)
        total_cost += subtotal
        categories.append({"category": category, "items": priced_items, "subtotal": subtotal})

    return json.dumps({"categories": categories, "total_cost": round(total_cost, 2)})
