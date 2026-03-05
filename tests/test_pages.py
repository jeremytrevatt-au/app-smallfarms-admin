from fastapi.testclient import TestClient

from app.main import app
from app import deps


client = TestClient(app)


def test_moderation_page_loads(monkeypatch):
    async def fake_list_submissions():
        return {"items": [{"id": "sub-123", "status": "pending"}]}

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Moderation Queue" in response.text


def test_billing_page_read_only(monkeypatch):
    async def fake_subscriptions():
        return {"items": [{"tenant_id": "t-1", "status": "active"}]}

    monkeypatch.setattr(deps.platform_client, "list_billing_subscriptions", fake_subscriptions)
    response = client.get("/billing")
    assert response.status_code == 200
    assert "Manual entitlement toggles are intentionally not available" in response.text


def test_harvest_page_loads():
    response = client.get("/harvest")
    assert response.status_code == 200
    assert "Workflow: run harvest preview, dry-run import selected candidates, then commit import." in response.text


def test_api_logs_page_loads():
    response = client.get("/api-logs")
    assert response.status_code == 200
    assert "API POST Logs" in response.text
