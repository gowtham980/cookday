from __future__ import annotations

from collections import defaultdict

from cookday_agent.schemas import (
    BudgetReport,
    DayContext,
    GroceryItem,
    GroceryList,
    Ingredient,
    Meal,
    MealPlan,
    Substitution,
    SubstitutionList,
)

CATEGORY_MAP = {
    "egg": "dairy",
    "milk": "dairy",
    "cheese": "dairy",
    "yogurt": "dairy",
    "bread": "bakery",
    "rice": "grains",
    "pasta": "grains",
    "oat": "grains",
    "chicken": "protein",
    "tofu": "protein",
    "bean": "protein",
    "lentil": "protein",
    "fish": "protein",
    "tomato": "produce",
    "onion": "produce",
    "garlic": "produce",
    "spinach": "produce",
    "lettuce": "produce",
    "pepper": "produce",
    "banana": "produce",
    "berry": "produce",
    "oil": "pantry",
    "salt": "pantry",
    "spice": "pantry",
    "sauce": "pantry",
}


def categorize(name: str) -> str:
    lower = name.lower()
    for key, cat in CATEGORY_MAP.items():
        if key in lower:
            return cat
    return "general"


def merge_ingredients(meals: MealPlan) -> GroceryList:
    buckets: dict[tuple[str, str], dict] = {}
    for meal in (meals.breakfast, meals.lunch, meals.dinner):
        for ing in meal.ingredients:
            key = (ing.name.strip().lower(), ing.unit.strip().lower())
            if key not in buckets:
                buckets[key] = {
                    "name": ing.name.strip(),
                    "qty": 0.0,
                    "unit": ing.unit,
                    "est_cost": 0.0,
                    "category": categorize(ing.name),
                }
            buckets[key]["qty"] += float(ing.qty)
            buckets[key]["est_cost"] += float(ing.est_cost)

    items = [
        GroceryItem(
            name=v["name"],
            qty=round(v["qty"], 2),
            unit=v["unit"],
            category=v["category"],
            est_cost=round(v["est_cost"], 2),
        )
        for v in sorted(buckets.values(), key=lambda x: (x["category"], x["name"]))
    ]
    return GroceryList(items=items)


def sum_grocery_cost(grocery: GroceryList) -> float:
    return round(sum(i.est_cost for i in grocery.items), 2)


def build_budget(limit: float, grocery: GroceryList) -> BudgetReport:
    total = sum_grocery_cost(grocery)
    feasible = total <= limit + 1e-6
    notes: list[str] = []
    swaps: list[str] = []
    if feasible:
        notes.append(f"Estimated ${total:.2f} is within your ${limit:.2f} budget.")
        headroom = limit - total
        if headroom > 5:
            notes.append(f"About ${headroom:.2f} headroom for snacks or extras.")
    else:
        over = total - limit
        notes.append(f"Over budget by ${over:.2f} (est. ${total:.2f} vs ${limit:.2f}).")
        expensive = sorted(grocery.items, key=lambda i: i.est_cost, reverse=True)[:3]
        for item in expensive:
            swaps.append(
                f"Swap or reduce '{item.name}' (~${item.est_cost:.2f}) for a cheaper protein/produce option."
            )
        swaps.append("Cook one pantry-based meal (rice/beans/eggs) to cut cost.")
    return BudgetReport(
        limit=limit,
        estimated_total=total,
        feasible=feasible,
        notes=notes,
        suggested_swaps=swaps,
    )


def build_substitutions(context: DayContext, meals: MealPlan) -> SubstitutionList:
    items: list[Substitution] = []
    avoid = {a.lower() for a in context.avoid}
    seen: set[str] = set()

    defaults = [
        Substitution(
            original="chicken",
            alternatives=["tofu", "chickpeas", "turkey"],
            reason="Protein swap for cost, diet, or availability",
        ),
        Substitution(
            original="dairy milk",
            alternatives=["oat milk", "almond milk", "soy milk"],
            reason="Lactose-free or vegan option",
        ),
        Substitution(
            original="white rice",
            alternatives=["brown rice", "quinoa", "cauliflower rice"],
            reason="Fiber or lower-carb preference",
        ),
    ]

    for meal in (meals.breakfast, meals.lunch, meals.dinner):
        for ing in meal.ingredients:
            name = ing.name.lower()
            if name in seen:
                continue
            for a in avoid:
                if a and a in name:
                    items.append(
                        Substitution(
                            original=ing.name,
                            alternatives=_alts_for(a),
                            reason=f"You asked to avoid '{a}'",
                        )
                    )
                    seen.add(name)
                    break

    for d in defaults:
        if d.original.lower() not in seen:
            items.append(d)
            seen.add(d.original.lower())

    return SubstitutionList(items=items[:8])


def _alts_for(avoid: str) -> list[str]:
    table = {
        "dairy": ["oat milk", "coconut yogurt", "vegan cheese"],
        "milk": ["oat milk", "almond milk"],
        "gluten": ["rice", "corn tortillas", "gluten-free pasta"],
        "nut": ["seeds", "sunflower butter"],
        "shellfish": ["tofu", "chicken", "white fish"],
        "meat": ["tofu", "lentils", "beans"],
        "spicy": ["mild paprika", "herbs only"],
    }
    for key, alts in table.items():
        if key in avoid:
            return alts
    return ["seasonal vegetable", "eggs", "beans"]


def mock_meal_plan(context: DayContext) -> MealPlan:
    """Deterministic plan for offline/demo/tests."""
    scale = max(1.0, context.people / 2.0)
    low_energy = context.energy == "low" or context.max_prep_minutes <= 25
    diet = context.diet.lower()
    vegetarian = any(x in diet for x in ("veg", "vegan", "plant"))

    def ing(name: str, qty: float, unit: str, cost: float) -> Ingredient:
        return Ingredient(name=name, qty=round(qty * scale, 2), unit=unit, est_cost=round(cost * scale, 2))

    if low_energy:
        breakfast = Meal(
            name="Greek yogurt parfait" if not vegetarian or "vegan" not in diet else "Overnight oats",
            minutes=10,
            steps=["Portion base", "Add fruit", "Top with seeds"],
            ingredients=[
                ing("rolled oats", 1, "cup", 0.8) if "vegan" in diet else ing("greek yogurt", 2, "cup", 3.0),
                ing("banana", 2, "count", 0.8),
                ing("berries", 1, "cup", 2.5),
            ],
        )
        lunch = Meal(
            name="Hummus veggie wrap",
            minutes=15,
            steps=["Warm tortilla", "Spread hummus", "Add veg", "Roll and pack"],
            ingredients=[
                ing("tortillas", 2, "count", 1.5),
                ing("hummus", 1, "cup", 2.0),
                ing("spinach", 2, "cup", 1.5),
                ing("cucumber", 1, "count", 0.8),
            ],
        )
        protein = "tofu" if vegetarian else "rotisserie chicken"
        dinner = Meal(
            name=f"Sheet-pan {protein} and vegetables",
            minutes=min(35, context.max_prep_minutes),
            steps=["Chop vegetables", f"Season {protein}", "Roast 20–25 min", "Serve with rice or leftovers"],
            ingredients=[
                ing(protein, 1, "lb", 6.0 if "chicken" in protein else 3.5),
                ing("mixed vegetables", 1.5, "lb", 4.0),
                ing("olive oil", 2, "tbsp", 0.4),
                ing("rice", 1.5, "cup", 1.2),
            ],
        )
    else:
        breakfast = Meal(
            name="Veggie omelette + toast" if not ("vegan" in diet) else "Tofu scramble + toast",
            minutes=20,
            steps=["Prep veg", "Cook protein base", "Toast bread", "Plate"],
            ingredients=[
                ing("eggs", 4, "count", 1.5) if "vegan" not in diet else ing("tofu", 0.75, "lb", 2.5),
                ing("bell pepper", 1, "count", 1.0),
                ing("onion", 0.5, "count", 0.4),
                ing("bread", 4, "slice", 1.0),
            ],
        )
        lunch = Meal(
            name="Grain bowl with beans",
            minutes=25,
            steps=["Cook grain", "Warm beans", "Assemble bowl", "Dress"],
            ingredients=[
                ing("quinoa or rice", 1.5, "cup", 2.0),
                ing("black beans", 1, "can", 1.2),
                ing("corn", 1, "cup", 0.8),
                ing("salsa", 0.5, "cup", 1.0),
                ing("avocado", 1, "count", 1.5),
            ],
        )
        dinner_protein = "chickpeas" if vegetarian else "chicken thighs"
        dinner = Meal(
            name=f"One-pot {dinner_protein} pasta" if not vegetarian else "Chickpea tomato pasta",
            minutes=min(40, context.max_prep_minutes),
            steps=["Sauté aromatics", "Add protein and sauce", "Simmer pasta", "Finish with herbs"],
            ingredients=[
                ing(dinner_protein, 1, "lb", 5.5 if "chicken" in dinner_protein else 1.5),
                ing("pasta", 12, "oz", 1.5),
                ing("tomato sauce", 1, "jar", 2.5),
                ing("garlic", 3, "clove", 0.3),
                ing("spinach", 2, "cup", 1.5),
            ],
        )

    # Filter avoided ingredients roughly
    avoid = [a.lower() for a in context.avoid]

    def scrub(meal: Meal) -> Meal:
        kept = [i for i in meal.ingredients if not any(a in i.name.lower() for a in avoid if a)]
        if len(kept) < len(meal.ingredients):
            kept.append(ing("extra vegetables", 1, "lb", 2.0))
        return meal.model_copy(update={"ingredients": kept})

    breakfast, lunch, dinner = scrub(breakfast), scrub(lunch), scrub(dinner)
    todos = [
        f"Prep {breakfast.name} (~{breakfast.minutes}m)",
        f"Prep {lunch.name} (~{lunch.minutes}m)",
        f"Cook {dinner.name} (~{dinner.minutes}m)",
        "Check pantry before shopping",
        "Pack leftovers if applicable",
    ]
    return MealPlan(breakfast=breakfast, lunch=lunch, dinner=dinner, cooking_todos=todos)


def estimate_ingredient_cost(name: str, qty: float = 1.0) -> float:
    """Tool-friendly cost heuristic for agents."""
    base = {
        "chicken": 6.0,
        "tofu": 3.0,
        "egg": 0.4,
        "rice": 0.5,
        "pasta": 1.5,
        "milk": 1.2,
        "cheese": 3.0,
        "vegetable": 2.0,
        "fruit": 1.5,
        "oil": 0.3,
        "bread": 0.4,
        "bean": 1.0,
    }
    lower = name.lower()
    unit = 2.0
    for k, v in base.items():
        if k in lower:
            unit = v
            break
    return round(unit * max(qty, 0.1), 2)
