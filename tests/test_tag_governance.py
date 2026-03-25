from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_tags_page_loads(monkeypatch):
    async def fake_list_canonical_tags():
        return {
            "items": [
                {"tag_code": "microgreens", "tag_label": "Microgreens", "is_active": True},
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_canonical_tags", fake_list_canonical_tags)
    response = client.get("/tags")
    assert response.status_code == 200
    assert "Canonical Tag Governance" in response.text
    assert "Canonical Tag Grid" in response.text


def test_upsert_tags_success(monkeypatch):
    async def fake_upsert_tags(requested_by, tags):
        assert requested_by == "admin@smallfarms"
        assert len(tags) == 1
        return {"requested_by": requested_by, "tags": [{"code": "microgreens"}]}

    async def fake_list_canonical_tags():
        return {
            "items": [
                {"tag_code": "microgreens", "tag_label": "Microgreens", "is_active": True},
            ]
        }

    monkeypatch.setattr(deps.platform_client, "upsert_tags", fake_upsert_tags)
    monkeypatch.setattr(deps.platform_client, "list_canonical_tags", fake_list_canonical_tags)

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


def test_upsert_tags_from_grid_rows(monkeypatch):
    captured = {"tags": None}

    async def fake_upsert_tags(requested_by, tags):
        assert requested_by == "admin@smallfarms"
        captured["tags"] = tags
        return {"ok": True}

    async def fake_list_canonical_tags():
        return {
            "items": [
                {"tag_code": "microgreens", "tag_label": "Microgreens", "is_active": True},
            ]
        }

    monkeypatch.setattr(deps.platform_client, "upsert_tags", fake_upsert_tags)
    monkeypatch.setattr(deps.platform_client, "list_canonical_tags", fake_list_canonical_tags)
    response = client.post(
        "/tags",
        data={
            "requested_by": "admin@smallfarms",
            "tag_name": "",
            "row_ids": ["0", "1"],
            "tag_code__0": "microgreens",
            "tag_label__0": "Microgreens",
            "is_active__0": "true",
            "tag_code__1": "flowers",
            "tag_label__1": "Flowers",
            "tags_json": "",
        },
    )
    assert response.status_code == 200
    assert captured["tags"] is not None
    assert len(captured["tags"]) == 2
    assert captured["tags"][1]["tag_code"] == "flowers"
