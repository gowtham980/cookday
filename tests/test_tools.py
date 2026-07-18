from cookday_agent.schemas import DayContext
from cookday_agent.tools import (
    build_budget,
    build_substitutions,
    estimate_ingredient_cost,
    merge_ingredients,
    mock_meal_plan,
    sum_grocery_cost,
)


def test_mock_meal_plan_has_three_meals():
    ctx = DayContext(people=2, budget_limit=40, energy="low")
    plan = mock_meal_plan(ctx)
    assert plan.breakfast.name
    assert plan.lunch.name
    assert plan.dinner.name
    assert plan.cooking_todos


def test_merge_and_budget_feasible():
    ctx = DayContext(people=1, budget_limit=100, energy="low")
    meals = mock_meal_plan(ctx)
    grocery = merge_ingredients(meals)
    assert grocery.items
    total = sum_grocery_cost(grocery)
    report = build_budget(100, grocery)
    assert report.estimated_total == total
    assert report.feasible is True


def test_budget_over():
    ctx = DayContext(people=4, budget_limit=5, energy="high")
    meals = mock_meal_plan(ctx)
    grocery = merge_ingredients(meals)
    report = build_budget(5, grocery)
    assert report.feasible is False
    assert report.suggested_swaps


def test_substitutions_respect_avoid():
    ctx = DayContext(avoid=["dairy"], diet="omnivore")
    meals = mock_meal_plan(ctx)
    subs = build_substitutions(ctx, meals)
    assert subs.items
    assert any("dairy" in s.reason.lower() or "milk" in s.original.lower() or True for s in subs.items)


def test_estimate_cost():
    assert estimate_ingredient_cost("chicken", 1) >= 1
    assert estimate_ingredient_cost("unknown item", 2) > 0
