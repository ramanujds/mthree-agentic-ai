"""
Meal Planner + Budgeting + Grocery Shopping app — CrewAI version.

Runs entirely against a local Ollama model, same setup as
../../rag-with-langchain/simple-rag-example-chromadb: no API key, nothing
leaves your machine. This is the CrewAI counterpart to
../../langchain/meal-planner-agent -- same problem, same Pydantic-shaped
output, built with CrewAI's Agent/Task/Crew abstractions instead of plain
LangChain (LCEL) code. See ../meal-planner-langchain-vs-crewai.md for the
full comparison.

Pipeline (three agents, one sequential Crew):
    1. meal_planner       -- Agent, output_pydantic=MealPlan
    2. shopping_organizer -- Agent + `price_lookup` tool, output_pydantic=ShoppingPlan
    3. budget_advisor      -- Agent, context=[shopping_task], output_pydantic=BudgetReport

Note on the tool: `llama3:8b` doesn't support Ollama's native tool-calling
API (confirmed directly -- Ollama returns "does not support tools" when you
try). CrewAI works around this itself: it falls back to its own
ReAct-style ("Thought/Action/Action Input") text prompting when native
function-calling fails, so tool use still works -- it just needs an
explicit example of the expected JSON in the task description, since an
8B model isn't reliable at inferring a tool's argument shape on its own.
"""

import os

from crewai import LLM, Agent, Crew, Process, Task

from models import BudgetReport, MealPlan, ShoppingPlan
from report import render_markdown_guide
from tools import price_lookup

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")

BUDGET = float(os.environ.get("MEAL_BUDGET", "40"))
DIET = os.environ.get("MEAL_DIET", "vegetarian")
NUM_MEALS = int(os.environ.get("MEAL_COUNT", "2"))


def build_crew() -> Crew:
    llm = LLM(model=f"ollama/{LLM_MODEL}", base_url=OLLAMA_BASE_URL, temperature=0.4)

    meal_planner = Agent(
        role="Meal Planner",
        goal="Suggest meals that match the user's budget and dietary needs",
        backstory="An expert home cook who plans balanced, affordable meals.",
        llm=llm,
    )

    shopping_organizer = Agent(
        role="Shopping Organizer",
        goal="Turn meal ingredients into a priced, categorized shopping list",
        backstory=(
            "A meticulous organizer who always calls the price_lookup tool exactly "
            "once, with every ingredient at once, and passes its result straight "
            "through as valid JSON."
        ),
        tools=[price_lookup],
        llm=llm,
    )

    budget_advisor = Agent(
        role="Budget Advisor",
        goal="Assess whether a shopping plan fits the budget and suggest savings",
        backstory="A frugal expert who finds cost-cutting swaps without sacrificing the meal plan.",
        llm=llm,
    )

    meal_planning_task = Task(
        description=(
            "Suggest {num_meals} {diet} meals that together cost no more than "
            "${budget} to make. For each meal, list its ingredients with realistic "
            "quantities (e.g. '2 lbs chicken breast'). Keep ingredient names simple "
            "and generic so they can be priced at a grocery store."
        ),
        expected_output="A structured meal plan with ingredients and quantities.",
        agent=meal_planner,
        output_pydantic=MealPlan,
    )

    shopping_task = Task(
        description=(
            "Using the meal plan above, collect every ingredient (with its quantity, "
            "e.g. '2 lbs chicken breast') from all meals into one list, then call the "
            "price_lookup tool EXACTLY ONCE with the full list. For example:\n"
            'Action Input: {"items": ["2 lbs chicken breast", "1 cup rice"]}\n'
            "Return the tool's JSON output as your final answer, unchanged."
        ),
        expected_output="A structured shopping plan grouped by category with a total cost.",
        agent=shopping_organizer,
        context=[meal_planning_task],
        output_pydantic=ShoppingPlan,
    )

    budget_task = Task(
        description=(
            "The user's grocery budget is ${budget}. Using the shopping plan's total "
            "cost from context, decide whether the plan is within budget, and write "
            "2-4 concrete, specific savings tips (e.g. cheaper ingredient swaps) even "
            "if already within budget. Write a short 2-3 sentence summary of the plan."
        ),
        expected_output="A structured budget report with savings tips and a summary.",
        agent=budget_advisor,
        context=[meal_planning_task, shopping_task],
        output_pydantic=BudgetReport,
    )

    return Crew(
        agents=[meal_planner, shopping_organizer, budget_advisor],
        tasks=[meal_planning_task, shopping_task, budget_task],
        process=Process.sequential,
    )


def main() -> None:
    crew = build_crew()

    print(f"Planning {NUM_MEALS} {DIET} meal(s) for a ${BUDGET:.2f} budget...\n")
    result = crew.kickoff(inputs={"budget": f"{BUDGET:.2f}", "diet": DIET, "num_meals": str(NUM_MEALS)})

    meal_plan: MealPlan = result.tasks_output[0].pydantic
    shopping_plan: ShoppingPlan = result.tasks_output[1].pydantic
    budget_report: BudgetReport = result.tasks_output[2].pydantic

    # Trust our own arithmetic (from the price_lookup tool) over the LLM's for
    # the numeric fields -- same approach as the LangChain version.
    budget_report.budget = BUDGET
    budget_report.total_cost = shopping_plan.total_cost
    budget_report.within_budget = shopping_plan.total_cost <= BUDGET

    guide = render_markdown_guide(meal_plan, shopping_plan, budget_report)
    out_path = os.path.join(os.path.dirname(__file__), "meal_plan_guide.md")
    with open(out_path, "w") as f:
        f.write(guide)

    print(f"\nTotal estimated cost: ${shopping_plan.total_cost:.2f}")
    print(f"Token usage: {result.token_usage}")
    print(f"Full guide written to {out_path}")


if __name__ == "__main__":
    main()
