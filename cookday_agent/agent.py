"""Google ADK agent definitions for CookDay.

Install optional deps: `pip install -e ".[adk]"` then use `adk web`.
Product UI uses cookday_agent.pipeline (mock by default; Ollama via litellm).
"""

from __future__ import annotations

import os

try:
    from google.adk.agents import LlmAgent, SequentialAgent
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "google-adk is optional. Install with: pip install -e '.[adk]'"
    ) from exc

from cookday_agent.tools import estimate_ingredient_cost


def _model():
    from google.adk.models.lite_llm import LiteLlm

    name = os.getenv("COOKDAY_OLLAMA_MODEL", "llama3.2")
    return LiteLlm(model=f"ollama_chat/{name}")


def build_root_agent() -> SequentialAgent:
    model = _model()

    meal_planner = LlmAgent(
        name="meal_planner",
        model=model,
        description="Plans breakfast, lunch, and dinner for one day with cooking steps.",
        instruction="""You are CookDay meal planner. Read the user day context.
Produce a clear breakfast, lunch, and dinner plan with ingredients (qty, unit, rough USD cost),
prep minutes, and step-by-step cooking todos. Respect diet, avoid list, time, energy, and budget.
""",
        output_key="meals",
    )

    grocery_agent = LlmAgent(
        name="grocery_agent",
        model=model,
        description="Builds a merged grocery list from the meal plan in state.",
        instruction="""Using session state key 'meals' (and the user message), produce a merged grocery list
with categories and estimated costs. Deduplicate ingredients.""",
        output_key="grocery",
    )

    substitution_agent = LlmAgent(
        name="substitution_agent",
        model=model,
        description="Suggests ingredient substitutions for diet, allergies, and cost.",
        instruction="""Using meals and user avoid/diet preferences, list practical substitutions
with reasons. Focus on allergens, missing pantry items, and budget.""",
        output_key="substitutions",
    )

    budget_agent = LlmAgent(
        name="budget_agent",
        model=model,
        description="Judges budget feasibility and suggests cost swaps.",
        instruction="""Using grocery estimates and the user's budget limit, say if the day is feasible.
Suggest concrete swaps if over budget. You may use tools for cost math.""",
        tools=[estimate_ingredient_cost],
        output_key="budget",
    )

    return SequentialAgent(
        name="cookday_pipeline",
        description="CookDay sequential pipeline: meals → grocery → substitutions → budget",
        sub_agents=[meal_planner, grocery_agent, substitution_agent, budget_agent],
    )


try:
    root_agent = build_root_agent()
except Exception:  # pragma: no cover
    root_agent = None  # type: ignore
