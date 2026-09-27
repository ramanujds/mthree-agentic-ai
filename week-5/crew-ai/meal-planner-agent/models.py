"""Pydantic models shared by every step of the meal-planning pipeline.

Using the same schema across steps means each step's output is a validated
object the next step can rely on, instead of free-form text to re-parse.
"""

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str = Field(description="Grocery item name, e.g. 'chicken breast'")
    quantity: str = Field(description="Amount needed, e.g. '1 lb' or '2 cups'")


class Meal(BaseModel):
    name: str = Field(description="Name of the dish")
    difficulty: str = Field(description="One of: easy, medium, hard")
    servings: int
    ingredients: list[Ingredient]


class MealPlan(BaseModel):
    meals: list[Meal]


class PricedItem(BaseModel):
    name: str
    quantity: str
    estimated_price: float
    category: str = Field(description="Store section, e.g. Produce, Meat, Dairy, Pantry")


class ShoppingCategory(BaseModel):
    category: str
    items: list[PricedItem]
    subtotal: float


class ShoppingPlan(BaseModel):
    categories: list[ShoppingCategory]
    total_cost: float


class BudgetReport(BaseModel):
    budget: float
    total_cost: float
    within_budget: bool
    savings_tips: list[str]
    summary: str
