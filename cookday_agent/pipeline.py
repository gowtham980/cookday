from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from cookday_agent.prompts import BUDGET, GROCERY, MEAL_PLANNER, SUBSTITUTIONS
from cookday_agent.schemas import (
    BudgetReport,
    DayContext,
    GroceryList,
    MealPlan,
    PlanResult,
    SubstitutionList,
)
from cookday_agent.tools import (
    build_budget,
    build_substitutions,
    merge_ingredients,
    mock_meal_plan,
)

logger = logging.getLogger(__name__)


def use_mock() -> bool:
    flag = os.getenv("COOKDAY_MOCK_LLM", "").lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    # Default mock if explicitly unset preference: try ollama, fall back handled in run
    return os.getenv("COOKDAY_FORCE_OLLAMA", "").lower() not in {"1", "true", "yes"}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def run_mock_pipeline(context: DayContext) -> PlanResult:
    meals = mock_meal_plan(context)
    grocery = merge_ingredients(meals)
    substitutions = build_substitutions(context, meals)
    budget = build_budget(context.budget_limit, grocery)
    return PlanResult(
        context=context,
        meals=meals,
        grocery=grocery,
        substitutions=substitutions,
        budget=budget,
        source="mock",
    )


async def _ollama_complete(prompt: str, model: str) -> str:
    """Call Ollama via LiteLLM (same path ADK LiteLlm uses)."""
    try:
        from litellm import acompletion
    except ImportError as exc:
        raise ImportError(
            "litellm required for Ollama mode. Install: pip install -e '.[ollama]'"
        ) from exc

    api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    response = await acompletion(
        model=f"ollama_chat/{model}",
        messages=[{"role": "user", "content": prompt}],
        api_base=api_base,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


async def run_ollama_pipeline(context: DayContext) -> PlanResult:
    model = os.getenv("COOKDAY_OLLAMA_MODEL", "llama3.2")
    ctx_json = context.model_dump_json()

    meals_raw = await _ollama_complete(
        MEAL_PLANNER.format(context_json=ctx_json), model
    )
    meals = MealPlan.model_validate(_extract_json(meals_raw))

    grocery_raw = await _ollama_complete(
        GROCERY.format(meals_json=meals.model_dump_json()), model
    )
    try:
        grocery = GroceryList.model_validate(_extract_json(grocery_raw))
        if not grocery.items:
            grocery = merge_ingredients(meals)
    except Exception:
        grocery = merge_ingredients(meals)

    subs_raw = await _ollama_complete(
        SUBSTITUTIONS.format(context_json=ctx_json, meals_json=meals.model_dump_json()),
        model,
    )
    try:
        substitutions = SubstitutionList.model_validate(_extract_json(subs_raw))
        if not substitutions.items:
            substitutions = build_substitutions(context, meals)
    except Exception:
        substitutions = build_substitutions(context, meals)

    # Deterministic budget from grocery costs (reliable vs free-form LLM math)
    budget = build_budget(context.budget_limit, grocery)
    # Optional LLM commentary merge
    try:
        budget_raw = await _ollama_complete(
            BUDGET.format(limit=context.budget_limit, grocery_json=grocery.model_dump_json()),
            model,
        )
        llm_budget = BudgetReport.model_validate(_extract_json(budget_raw))
        budget.notes = list(dict.fromkeys(budget.notes + llm_budget.notes))
        budget.suggested_swaps = list(
            dict.fromkeys(budget.suggested_swaps + llm_budget.suggested_swaps)
        )
    except Exception:
        pass

    return PlanResult(
        context=context,
        meals=meals,
        grocery=grocery,
        substitutions=substitutions,
        budget=budget,
        source="ollama",
    )


async def run_pipeline(context: DayContext) -> PlanResult:
    """
    Primary entry: mock by default unless COOKDAY_FORCE_OLLAMA=1.
    If Ollama fails, fall back to mock (hybrid).
    """
    force = os.getenv("COOKDAY_FORCE_OLLAMA", "").lower() in {"1", "true", "yes"}
    mock_only = os.getenv("COOKDAY_MOCK_LLM", "1").lower() in {"1", "true", "yes", ""}

    if mock_only and not force:
        return run_mock_pipeline(context)

    try:
        return await run_ollama_pipeline(context)
    except Exception as exc:
        logger.warning("Ollama pipeline failed (%s); using mock fallback", exc)
        result = run_mock_pipeline(context)
        result.source = "hybrid"
        return result
