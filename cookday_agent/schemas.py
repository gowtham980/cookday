from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Ingredient(BaseModel):
    name: str
    qty: float = 1.0
    unit: str = "unit"
    est_cost: float = Field(default=1.0, ge=0)


class Meal(BaseModel):
    name: str
    minutes: int = Field(default=20, ge=1, le=240)
    steps: list[str] = Field(default_factory=list)
    ingredients: list[Ingredient] = Field(default_factory=list)


class MealPlan(BaseModel):
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    cooking_todos: list[str] = Field(default_factory=list)


class GroceryItem(BaseModel):
    name: str
    qty: float = 1.0
    unit: str = "unit"
    category: str = "general"
    est_cost: float = Field(default=1.0, ge=0)


class GroceryList(BaseModel):
    items: list[GroceryItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Substitution(BaseModel):
    original: str
    alternatives: list[str] = Field(default_factory=list)
    reason: str = ""


class SubstitutionList(BaseModel):
    items: list[Substitution] = Field(default_factory=list)


class BudgetReport(BaseModel):
    limit: float
    estimated_total: float
    feasible: bool
    notes: list[str] = Field(default_factory=list)
    suggested_swaps: list[str] = Field(default_factory=list)


class DayContext(BaseModel):
    people: int = Field(default=2, ge=1, le=12)
    budget_limit: float = Field(default=40.0, ge=0)
    max_prep_minutes: int = Field(default=45, ge=5, le=240)
    diet: str = "omnivore"
    avoid: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    energy: Literal["low", "medium", "high"] = "medium"
    notes: str = ""

    @field_validator("avoid", "equipment", mode="before")
    @classmethod
    def split_csv(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v


class PlanResult(BaseModel):
    context: DayContext
    meals: MealPlan
    grocery: GroceryList
    substitutions: SubstitutionList
    budget: BudgetReport
    source: Literal["mock", "ollama", "hybrid"] = "mock"
