from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_listing_tags_page_loads(monkeypatch):
    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        assert listing_name == ""
        assert tag_name == ""
        assert page == 1
        assert page_size == 25
        assert group_by_listing is False
        return {
            "items": [
                {
                    "listing_id": "listing-1",
                    "listing_name": "Example Farm",
                    "tag_code": "microgreens",
                    "tag_name": "Microgreens",
                    "assigned_at": "2026-03-25T04:01:00Z",
                    "assigned_by": "admin@smallfarms.com.au",
                    "is_active_assignment": True,
                }
            ],
            "page": 1,
            "page_size": 25,
            "total": 1,
        }

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_assignments",
        fake_list_listing_tag_assignments,
    )
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "Listing Tag Assignments" in response.text
    assert "Example Farm" in response.text
    assert "Microgreens" in response.text


def test_listing_tags_filters_forwarded(monkeypatch):
    seen = {}

    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        seen["listing_name"] = listing_name
        seen["tag_name"] = tag_name
        seen["page"] = page
        seen["page_size"] = page_size
        seen["group_by_listing"] = group_by_listing
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_assignments",
        fake_list_listing_tag_assignments,
    )
    response = client.get(
        "/listing-tags?listing_name=Example&tag_name=Micro&page=2&page_size=10&group_by_listing=false"
    )
    assert response.status_code == 200
    assert seen["listing_name"] == "Example"
    assert seen["tag_name"] == "Micro"
    assert seen["page"] == 2
    assert seen["page_size"] == 10
    assert seen["group_by_listing"] is False


def test_listing_tags_grouped_view(monkeypatch):
    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        assert group_by_listing is True
        return {
            "items": [],
            "grouped_items": [
                {
                    "listing_id": "listing-1",
                    "listing_name": "Example Farm",
                    "latest_assigned_at": "2026-03-25T04:30:00Z",
                    "tags": [
                        {
                            "tag_code": "microgreens",
                            "tag_name": "Microgreens",
                            "assigned_at": "2026-03-25T04:01:00Z",
                            "assigned_by": "admin@smallfarms.com.au",
                        }
                    ],
                }
            ],
            "page": 1,
            "page_size": 25,
            "total": 1,
        }

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_assignments",
        fake_list_listing_tag_assignments,
    )
    response = client.get("/listing-tags?group_by_listing=true")
    assert response.status_code == 200
    assert "Grouped Assignments" in response.text
    assert "Example Farm" in response.text
    assert "latest_assigned_at" not in response.text


def test_listing_tags_load_error_503(monkeypatch):
    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        raise PlatformApiError(503, "database_unavailable", "database_unavailable")

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_assignments",
        fake_list_listing_tag_assignments,
    )
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "database_unavailable: listing tag assignment service unavailable." in response.text


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
