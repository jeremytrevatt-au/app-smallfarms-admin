from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.api_log_store import api_log_store
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def _mock_canonical_tags(monkeypatch):
    async def fake_list_canonical_tags():
        return {
            "items": [
                {"tag_code": "microgreens", "tag_name": "Microgreens", "is_active": True},
                {"tag_code": "flowers", "tag_name": "Flowers", "is_active": True},
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_canonical_tags", fake_list_canonical_tags)


def test_listing_tags_page_loads(monkeypatch):
    _mock_canonical_tags(monkeypatch)

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
        if group_by_listing:
            assert page_size == 100
            return {"grouped_items": [], "page": 1, "page_size": 100, "total": 0}
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
    assert "Listing Tag Editor" in response.text


def test_listing_tags_filters_forwarded(monkeypatch):
    _mock_canonical_tags(monkeypatch)
    calls = []

    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        calls.append(
            {
                "listing_name": listing_name,
                "tag_name": tag_name,
                "page": page,
                "page_size": page_size,
                "group_by_listing": group_by_listing,
            }
        )
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
    assert calls[0]["listing_name"] == "Example"
    assert calls[0]["tag_name"] == "Micro"
    assert calls[0]["page"] == 2
    assert calls[0]["page_size"] == 10
    assert calls[0]["group_by_listing"] is False
    assert calls[1]["listing_name"] == "Example"
    assert calls[1]["tag_name"] == ""
    assert calls[1]["page"] == 1
    assert calls[1]["group_by_listing"] is True


def test_listing_tags_grouped_view(monkeypatch):
    _mock_canonical_tags(monkeypatch)

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
    _mock_canonical_tags(monkeypatch)

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


def test_listing_tags_page_shows_related_api_logs(monkeypatch):
    _mock_canonical_tags(monkeypatch)

    async def fake_list_listing_tag_assignments(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        group_by_listing=False,
    ):
        return {"items": [], "page": 1, "page_size": 25, "total": 0}

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_assignments",
        fake_list_listing_tag_assignments,
    )
    api_log_store.add(
        {
            "started_at_utc": "2026-03-25T07:10:00+00:00",
            "finished_at_utc": "2026-03-25T07:10:00+00:00",
            "method": "GET",
            "path": "/v1/admin/listing-tag-assignments",
            "request_body": {},
            "request_query": {"listing_name": "example"},
            "status_code": 404,
            "response_body": {"detail": "Not Found"},
            "latency_ms": 100,
        }
    )
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "API Request/Response Log" in response.text
    assert "/v1/admin/listing-tag-assignments" in response.text
    assert "Not Found" in response.text


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


def test_replace_listing_tags_from_checkboxes(monkeypatch):
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
            "tag_codes": ["microgreens", "flowers"],
            "reason_code": "ADMIN_TAXONOMY_UPDATE",
            "requested_by": "admin@smallfarms",
        },
    )

    assert response.status_code == 200
    assert "Listing tag assignments updated." in response.text
