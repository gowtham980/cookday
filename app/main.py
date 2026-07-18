from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cookday_agent.pipeline import run_pipeline
from cookday_agent.schemas import DayContext

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(
    title="CookDay",
    description="AI cooking day planner — meals, grocery, substitutions, budget",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.get("/health")
async def health():
    mock = os.getenv("COOKDAY_MOCK_LLM", "1").lower() in {"1", "true", "yes", ""}
    force = os.getenv("COOKDAY_FORCE_OLLAMA", "").lower() in {"1", "true", "yes"}
    return {
        "status": "ok",
        "mock_default": mock and not force,
        "ollama_model": os.getenv("COOKDAY_OLLAMA_MODEL", "llama3.2"),
        "ollama_api_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"result": None, "error": None, "form": _default_form()},
    )


@app.post("/plan", response_class=HTMLResponse)
async def plan_form(
    request: Request,
    people: int = Form(2),
    budget_limit: float = Form(40.0),
    max_prep_minutes: int = Form(45),
    diet: str = Form("omnivore"),
    avoid: str = Form(""),
    equipment: str = Form(""),
    energy: str = Form("medium"),
    notes: str = Form(""),
    tab: str = Form("meals"),
):
    form = {
        "people": people,
        "budget_limit": budget_limit,
        "max_prep_minutes": max_prep_minutes,
        "diet": diet,
        "avoid": avoid,
        "equipment": equipment,
        "energy": energy,
        "notes": notes,
    }
    try:
        context = DayContext(
            people=people,
            budget_limit=budget_limit,
            max_prep_minutes=max_prep_minutes,
            diet=diet,
            avoid=avoid,
            equipment=equipment,
            energy=energy,  # type: ignore[arg-type]
            notes=notes,
        )
        result = await run_pipeline(context)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "result": result,
                "error": None,
                "form": form,
                "active_tab": tab if tab in {"meals", "grocery", "subs", "budget"} else "meals",
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "result": None,
                "error": str(exc),
                "form": form,
                "active_tab": "meals",
            },
            status_code=400,
        )


@app.post("/api/plan")
async def plan_api(context: DayContext):
    result = await run_pipeline(context)
    return JSONResponse(result.model_dump())


def _default_form() -> dict:
    return {
        "people": 2,
        "budget_limit": 40,
        "max_prep_minutes": 45,
        "diet": "omnivore",
        "avoid": "",
        "equipment": "stove, oven",
        "energy": "medium",
        "notes": "",
    }


def run() -> None:
    import uvicorn

    host = os.getenv("COOKDAY_HOST", "0.0.0.0")
    port = int(os.getenv("PORT") or os.getenv("COOKDAY_PORT", "8080"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
