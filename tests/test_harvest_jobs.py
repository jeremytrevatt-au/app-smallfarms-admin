from fastapi.testclient import TestClient

from app.main import app
from app import deps


client = TestClient(app)


def test_harvest_preview_sends_required_contract_fields(monkeypatch):
    captured = {"payload": None}

    async def fake_create_harvest_job(payload):
        captured["payload"] = payload
        return {
            "job_id": "job-1",
            "query_text": "microgreens shop melbourne",
            "effective_query_text": "microgreens farm melbourne",
            "query_attempts": 2,
            "places_provider_status": "OK",
            "preview_results": [
                {
                    "provider_place_id": "p-1",
                    "name": "Zulu Place",
                    "formatted_address": "123 Test St",
                    "types": ["produce_store"],
                    "exists_in_database": True,
                    "existing_listing_id": "listing-1",
                },
                {
                    "provider_place_id": "p-2",
                    "name": "Alpha Place",
                    "formatted_address": "55 Example St",
                    "types": ["produce_store"],
                    "exists_in_database": False,
                    "existing_listing_id": None,
                }
            ],
        }

    monkeypatch.setattr(deps.platform_client, "create_harvest_job", fake_create_harvest_job)

    response = client.post(
        "/harvest/jobs",
        data={
            "query_text": "microgreens shop melbourne",
            "search_scope": "directory_preview",
            "region_hint": "melbourne",
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
    assert captured["payload"]["region_hint"] == "melbourne"
    assert captured["payload"]["search_scope"] == "directory_preview"
    assert captured["payload"]["category_codes"] == ["produce", "flowers"]
    assert captured["payload"]["max_requests"] == 10
    assert captured["payload"]["max_runtime_minutes"] == 5
    assert captured["payload"]["priority_code"] == "normal"
    assert captured["payload"]["requested_by"] == "admin@smallfarms"
    assert "Select All" in response.text
    assert "Select None" in response.text
    assert "Dry Run Selected" in response.text
    assert "Query diagnostics" in response.text
    assert "microgreens farm melbourne" in response.text
    assert response.text.find("Alpha Place") < response.text.find("Zulu Place")
    assert "id=\"candidate-summary\"" in response.text
    assert "Exists In Database" in response.text
    assert "Existing Listing ID" in response.text


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
