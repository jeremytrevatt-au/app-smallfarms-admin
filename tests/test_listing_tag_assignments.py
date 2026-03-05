from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_listing_tags_page_loads():
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "Listing Tag Assignments" in response.text


def test_replace_listing_tags_success(monkeypatch):
    async def fake_replace_listing_tag_assignments(listing_id, tag_codes, reason_code, requested_by):
        assert listing_id == "listing-1"
        assert tag_codes == ["microgreens", "flowers"]
        assert reason_code == "ADMIN_TAXONOMY_UPDATE"
        assert requested_by == "admin@smallfarms"
        return {"listing_id": listing_id, "tag_codes": tag_codes}

    monkeypatch.setattr(
        deps.platform_client, "replace_listing_tag_assignments", fake_replace_listing_tag_assignments
    )

    response = client.post(
        "/listing-tags",
        data={
            "listing_id": "listing-1",
            "tag_codes_csv": "microgreens,flowers",
            "reason_code": "ADMIN_TAXONOMY_UPDATE",
            "requested_by": "admin@smallfarms",
        },
    )

    assert response.status_code == 200
    assert "Listing tag assignments updated." in response.text


def test_replace_listing_tags_unknown_code(monkeypatch):
    async def fake_replace_listing_tag_assignments(listing_id, tag_codes, reason_code, requested_by):
        assert listing_id == "listing-1"
        assert tag_codes == ["unknown_tag"]
        assert reason_code == "ADMIN_TAXONOMY_UPDATE"
        assert requested_by == "admin@smallfarms"
        raise PlatformApiError(422, "validation_failed", "validation_failed")

    monkeypatch.setattr(
        deps.platform_client, "replace_listing_tag_assignments", fake_replace_listing_tag_assignments
    )

    response = client.post(
        "/listing-tags",
        data={
            "listing_id": "listing-1",
            "tag_codes_csv": "unknown_tag",
            "reason_code": "ADMIN_TAXONOMY_UPDATE",
            "requested_by": "admin@smallfarms",
        },
    )

    assert response.status_code == 200
    assert "unknown or inactive" in response.text
