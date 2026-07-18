import os

import pytest
from fastapi.testclient import TestClient

os.environ["COOKDAY_MOCK_LLM"] = "1"

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_home():
    r = client.get("/")
    assert r.status_code == 200
    assert "CookDay" in r.text
    assert "Build my cooking day" in r.text


def test_api_plan():
    r = client.post(
        "/api/plan",
        json={
            "people": 2,
            "budget_limit": 35,
            "max_prep_minutes": 30,
            "diet": "omnivore",
            "avoid": ["shellfish"],
            "energy": "low",
            "notes": "test",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "meals" in data
    assert "grocery" in data
    assert "substitutions" in data
    assert "budget" in data
    assert data["meals"]["breakfast"]["name"]
    assert data["budget"]["limit"] == 35


def test_form_plan():
    r = client.post(
        "/plan",
        data={
            "people": "2",
            "budget_limit": "40",
            "max_prep_minutes": "45",
            "diet": "omnivore",
            "avoid": "",
            "equipment": "stove",
            "energy": "medium",
            "notes": "form test",
        },
    )
    assert r.status_code == 200
    assert "Breakfast" in r.text or "breakfast" in r.text.lower()
    assert "Grocery" in r.text
