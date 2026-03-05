from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_tags_page_loads():
    response = client.get("/tags")
    assert response.status_code == 200
    assert "Canonical Tag Governance" in response.text


def test_upsert_tags_success(monkeypatch):
    async def fake_upsert_tags(requested_by, tags):
        assert requested_by == "admin@smallfarms"
        assert len(tags) == 1
        return {"requested_by": requested_by, "tags": [{"code": "microgreens"}]}

    monkeypatch.setattr(deps.platform_client, "upsert_tags", fake_upsert_tags)

    response = client.post(
        "/tags",
        data={
            "requested_by": "admin@smallfarms",
            "tags_json": '[{"tag_code":"microgreens","tag_label":"Microgreens","is_active":true}]',
        },
    )

    assert response.status_code == 200
    assert "Canonical tags updated." in response.text


def test_upsert_tags_validation_error(monkeypatch):
    async def fake_upsert_tags(_requested_by, _tags):
        raise PlatformApiError(422, "validation_failed", "validation_failed")

    monkeypatch.setattr(deps.platform_client, "upsert_tags", fake_upsert_tags)

    response = client.post(
        "/tags",
        data={
            "requested_by": "admin@smallfarms",
            "tags_json": '[{"tag_code":"bad","tag_label":"Bad"}]',
        },
    )

    assert response.status_code == 200
    assert "validation_failed" in response.text
