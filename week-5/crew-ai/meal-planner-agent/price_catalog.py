"""A tiny local grocery price/category catalog.

Real pricing would come from a store API or a web-search tool (SerperDev,
etc.), but that needs an API key. This keeps the whole app runnable fully
offline, matching the local-Ollama, no-API-key setup of the RAG example
this project borrows its LLM config from.
"""

_CATALOG: dict[str, float] = {
    "chicken breast": 4.99,
    "chicken thigh": 3.49,
    "ground beef": 5.99,
    "tofu": 2.49,
    "eggs": 3.29,
    "milk": 3.99,
    "cheese": 4.49,
    "parmesan cheese": 4.99,
    "yogurt": 3.79,
    "pasta": 1.99,
    "rice": 2.49,
    "bread": 2.99,
    "tortilla": 2.79,
    "black beans": 1.29,
    "chickpeas": 1.29,
    "lentils": 1.99,
    "onion": 0.79,
    "garlic": 0.59,
    "tomato": 1.49,
    "bell pepper": 1.29,
    "spinach": 2.49,
    "broccoli": 1.99,
    "carrot": 0.99,
    "potato": 1.49,
    "olive oil": 6.99,
    "butter": 3.49,
    "salt": 0.99,
    "pepper": 1.49,
    "basil": 1.99,
    "oregano": 1.99,
    "mixed vegetables": 2.49,
    "avocado": 1.49,
    "salsa": 2.99,
    "sour cream": 2.49,
    "corn": 1.29,
}

_CATEGORY_BY_KEYWORD: dict[str, str] = {
    "chicken": "Meat",
    "beef": "Meat",
    "tofu": "Protein",
    "egg": "Dairy",
    "milk": "Dairy",
    "cheese": "Dairy",
    "yogurt": "Dairy",
    "butter": "Dairy",
    "sour cream": "Dairy",
    "pasta": "Pantry",
    "rice": "Pantry",
    "bread": "Bakery",
    "tortilla": "Bakery",
    "bean": "Pantry",
    "chickpea": "Pantry",
    "lentil": "Pantry",
    "salt": "Pantry",
    "pepper": "Pantry",
    "oil": "Pantry",
    "basil": "Pantry",
    "oregano": "Pantry",
    "salsa": "Pantry",
    "onion": "Produce",
    "garlic": "Produce",
    "tomato": "Produce",
    "spinach": "Produce",
    "broccoli": "Produce",
    "carrot": "Produce",
    "potato": "Produce",
    "avocado": "Produce",
    "vegetable": "Produce",
    "corn": "Produce",
}

DEFAULT_PRICE = 2.50
DEFAULT_CATEGORY = "Pantry"


def lookup_price(item: str) -> float:
    """Return an estimated USD price for a grocery item name."""
    key = item.strip().lower()
    for catalog_key, price in _CATALOG.items():
        if catalog_key in key or key in catalog_key:
            return price
    return DEFAULT_PRICE


def lookup_category(item: str) -> str:
    """Return a store section/category for a grocery item name."""
    key = item.strip().lower()
    for keyword, category in _CATEGORY_BY_KEYWORD.items():
        if keyword in key:
            return category
    return DEFAULT_CATEGORY
