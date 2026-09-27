"""Renders the three pipeline outputs into a single human-readable Markdown guide."""

from models import BudgetReport, MealPlan, ShoppingPlan


def render_markdown_guide(meal_plan: MealPlan, shopping_plan: ShoppingPlan, budget_report: BudgetReport) -> str:
    lines: list[str] = ["# Your Meal Planning Guide", ""]

    lines.append("## Meals")
    for meal in meal_plan.meals:
        lines.append(f"### {meal.name} ({meal.difficulty}, serves {meal.servings})")
        for ing in meal.ingredients:
            lines.append(f"- {ing.quantity} {ing.name}")
        lines.append("")

    lines.append("## Shopping List")
    for category in shopping_plan.categories:
        lines.append(f"### {category.category} — ${category.subtotal:.2f}")
        for item in category.items:
            # The price_lookup tool folds quantity into `name` (e.g. "2 cups rice"),
            # since it only receives a flat list of ingredient strings.
            lines.append(f"- {item.name} — ${item.estimated_price:.2f}")
        lines.append("")
    lines.append(f"**Total estimated cost: ${shopping_plan.total_cost:.2f}**")
    lines.append("")

    lines.append("## Budget")
    status = "within budget ✅" if budget_report.within_budget else "over budget ⚠️"
    lines.append(f"Budget: ${budget_report.budget:.2f} — Estimated cost: ${budget_report.total_cost:.2f} ({status})")
    lines.append("")
    lines.append(budget_report.summary)
    lines.append("")
    if budget_report.savings_tips:
        lines.append("### Savings tips")
        for tip in budget_report.savings_tips:
            lines.append(f"- {tip}")

    return "\n".join(lines)
