from fastapi.testclient import TestClient

from app.main import app
from app import deps


client = TestClient(app)


def test_reject_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_reject(_submission_id, _reason_code, _note):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "reject_submission", fake_reject)

    response = client.post(
        "/moderation/sub-1/reject",
        data={"reason_code": "", "note": "no reason"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_request_changes_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_request_changes(_submission_id, _reason_code, _note):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "request_changes", fake_request_changes)

    response = client.post(
        "/moderation/sub-1/request-changes",
        data={"reason_code": "", "note": "missing metadata"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_escalate_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_escalate(_submission_id, _reason_code, _note):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "escalate_submission", fake_escalate)

    response = client.post(
        "/moderation/sub-1/escalate",
        data={"reason_code": "", "note": "needs legal"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False
