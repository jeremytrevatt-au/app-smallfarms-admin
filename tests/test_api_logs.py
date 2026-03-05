from fastapi.testclient import TestClient

from app.main import app
from app.services.api_log_store import api_log_store


client = TestClient(app)


def test_api_logs_page_shows_record():
    api_log_store.add(
        {
            "started_at_utc": "2026-03-05T00:00:00+00:00",
            "finished_at_utc": "2026-03-05T00:00:01+00:00",
            "method": "POST",
            "path": "/v1/admin/harvest/jobs",
            "request_body": {"source": "places-sync-preview"},
            "status_code": 200,
            "response_body": {"ok": True},
            "latency_ms": 1000,
        }
    )
    response = client.get("/api-logs")
    assert response.status_code == 200
    assert "/v1/admin/harvest/jobs" in response.text
