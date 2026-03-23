from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_reject_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_reject(
        _submission_id,
        _current_status,
        _actor_id,
        _actor_role,
        _reason_code,
        _review_notes,
    ):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "reject_submission", fake_reject)

    response = client.post(
        "/moderation/sub-1/reject",
        data={
            "current_status": "submitted_pending_review",
            "actor_id": "admin@smallfarms.com.au",
            "actor_role": "admin_operator",
            "reason_code": "",
            "note": "no reason",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_request_changes_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_request_changes(
        _submission_id,
        _current_status,
        _actor_id,
        _actor_role,
        _reason_code,
        _review_notes,
    ):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "request_changes", fake_request_changes)

    response = client.post(
        "/moderation/sub-1/request-changes",
        data={
            "current_status": "submitted_pending_review",
            "actor_id": "admin@smallfarms.com.au",
            "actor_role": "admin_operator",
            "reason_code": "",
            "note": "missing metadata",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_escalate_requires_reason_code(monkeypatch):
    called = {"value": False}

    async def fake_escalate(
        _submission_id,
        _current_status,
        _actor_id,
        _actor_role,
        _reason_code,
    ):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "escalate_submission", fake_escalate)

    response = client.post(
        "/moderation/sub-1/escalate",
        data={
            "current_status": "submitted_pending_review",
            "actor_id": "admin@smallfarms.com.au",
            "actor_role": "admin_operator",
            "reason_code": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_approve_requires_actor_and_status(monkeypatch):
    called = {"value": False}

    async def fake_approve(
        _submission_id,
        _current_status,
        _actor_id,
        _actor_role,
        _approval_note,
    ):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "approve_submission", fake_approve)

    response = client.post(
        "/moderation/sub-1/approve",
        data={"current_status": "", "actor_id": "", "actor_role": "", "approval_note": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_resolve_escalation_requires_resolution(monkeypatch):
    called = {"value": False}

    async def fake_resolve(
        _submission_id,
        _actor_id,
        _actor_role,
        _resolution,
        _review_notes,
    ):
        called["value"] = True
        return {}

    monkeypatch.setattr(deps.platform_client, "resolve_escalation", fake_resolve)

    response = client.post(
        "/moderation/sub-1/resolve-escalation",
        data={
            "actor_id": "admin@smallfarms.com.au",
            "actor_role": "admin_operator",
            "resolution": "",
            "review_notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "level=error" in response.headers["location"]
    assert called["value"] is False


def test_approve_maps_status_conflict_error(monkeypatch):
    async def fake_approve(**_kwargs):
        raise PlatformApiError(
            409,
            "stale status",
            "moderation_status_conflict",
        )

    monkeypatch.setattr(deps.platform_client, "approve_submission", fake_approve)

    response = client.post(
        "/moderation/sub-1/approve",
        data={
            "current_status": "submitted_pending_review",
            "actor_id": "admin@smallfarms.com.au",
            "actor_role": "admin_operator",
            "approval_note": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "Submission+status+changed.+Refresh+the+queue+and+retry." in response.headers["location"]
