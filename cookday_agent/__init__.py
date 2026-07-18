"""CookDay ADK agents and planning pipeline."""

from cookday_agent.pipeline import run_mock_pipeline, run_pipeline
from cookday_agent.schemas import DayContext, PlanResult

__all__ = [
    "DayContext",
    "PlanResult",
    "run_pipeline",
    "run_mock_pipeline",
]

# Optional ADK root_agent for `adk web`
try:
    from cookday_agent.agent import root_agent  # noqa: F401

    __all__.append("root_agent")
except Exception:
    pass
