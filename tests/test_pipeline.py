import asyncio
import os

from cookday_agent.pipeline import run_mock_pipeline, run_pipeline
from cookday_agent.schemas import DayContext


def test_mock_pipeline_complete():
    ctx = DayContext(
        people=2,
        budget_limit=40,
        max_prep_minutes=30,
        diet="vegetarian",
        avoid=["meat"],
        energy="low",
        notes="Weeknight",
    )
    result = run_mock_pipeline(ctx)
    assert result.source == "mock"
    assert result.meals.breakfast.name
    assert result.grocery.items
    assert result.substitutions.items
    assert result.budget.limit == 40


def test_run_pipeline_defaults_to_mock(monkeypatch):
    monkeypatch.setenv("COOKDAY_MOCK_LLM", "1")
    monkeypatch.delenv("COOKDAY_FORCE_OLLAMA", raising=False)
    result = asyncio.run(run_pipeline(DayContext()))
    assert result.source == "mock"
    assert len(result.grocery.items) >= 1
