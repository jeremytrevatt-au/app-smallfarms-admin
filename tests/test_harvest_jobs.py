from fastapi.testclient import TestClient

from app.main import app
from app import deps


client = TestClient(app)


def test_harvest_preview_sends_required_contract_fields(monkeypatch):
    captured = {"payload": None}

    async def fake_create_harvest_job(payload):
        captured["payload"] = payload
        return {"job_id": "job-1"}

    monkeypatch.setattr(deps.platform_client, "create_harvest_job", fake_create_harvest_job)

    response = client.post(
        "/harvest/jobs",
        data={
            "query_text": "microgreens shop melbourne",
            "search_scope": "directory_preview",
            "category_codes_csv": "produce,flowers",
            "max_requests": "10",
            "max_runtime_minutes": "5",
            "priority_code": "normal",
            "requested_by": "admin@smallfarms",
            "note": "",
        },
    )

    assert response.status_code == 200
    assert captured["payload"] is not None
    assert captured["payload"]["query_text"] == "microgreens shop melbourne"
    assert captured["payload"]["search_scope"] == "directory_preview"
    assert captured["payload"]["category_codes"] == ["produce", "flowers"]
    assert captured["payload"]["max_requests"] == 10
    assert captured["payload"]["max_runtime_minutes"] == 5
    assert captured["payload"]["priority_code"] == "normal"
    assert captured["payload"]["requested_by"] == "admin@smallfarms"


def test_harvest_preview_missing_fields_returns_validation_message():
    response = client.post(
        "/harvest/jobs",
        data={
            "query_text": "",
            "note": "",
        },
    )

    assert response.status_code == 200
    assert "Harvest request is invalid. Required:" in response.text
    assert "query_text" in response.text
