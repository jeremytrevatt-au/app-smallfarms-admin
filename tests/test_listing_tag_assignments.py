from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.api_log_store import api_log_store
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def _mock_listing_tag_matrix(monkeypatch):
    async def fake_list_listing_tag_matrix(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        include_inactive_tags=False,
    ):
        assert include_inactive_tags is False
        return {
            "tags": [
                {"tag_code": "microgreens", "tag_name": "Microgreens", "is_active": True},
                {"tag_code": "flowers", "tag_name": "Flowers", "is_active": True},
            ],
            "items": [
                {
                    "listing_id": "listing-1",
                    "display_name": "Example Farm",
                    "assigned_tag_codes": ["microgreens"],
                },
                {
                    "listing_id": "listing-2",
                    "display_name": "Beta Farm",
                    "assigned_tag_codes": [],
                },
            ],
            "page": page,
            "page_size": page_size,
            "total": 2,
        }

    monkeypatch.setattr(deps.platform_client, "list_listing_tag_matrix", fake_list_listing_tag_matrix)


def test_listing_tags_page_loads(monkeypatch):
    _mock_listing_tag_matrix(monkeypatch)
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "Listing Tag Assignments" in response.text
    assert "Example Farm" in response.text
    assert "Microgreens" in response.text
    assert "Listing/Tag Matrix Editor" in response.text


def test_listing_tags_filters_forwarded(monkeypatch):
    seen = {}
    calls = []

    async def fake_list_listing_tag_matrix(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        include_inactive_tags=False,
    ):
        seen["include_inactive_tags"] = include_inactive_tags
        calls.append(
            {
                "listing_name": listing_name,
                "tag_name": tag_name,
                "page": page,
                "page_size": page_size,
            }
        )
        return {"tags": [], "items": [], "page": page, "page_size": page_size, "total": 0}

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_matrix",
        fake_list_listing_tag_matrix,
    )
    response = client.get(
        "/listing-tags?listing_name=Example&tag_name=Micro&page=2&page_size=10&group_by_listing=false"
    )
    assert response.status_code == 200
    assert calls[0]["listing_name"] == "Example"
    assert calls[0]["tag_name"] == "Micro"
    assert calls[0]["page"] == 2
    assert calls[0]["page_size"] == 10
    assert seen["include_inactive_tags"] is False


def test_listing_tags_grouped_view(monkeypatch):
    _mock_listing_tag_matrix(monkeypatch)
    response = client.get("/listing-tags?group_by_listing=true")
    assert response.status_code == 200
    assert "Listing/Tag Matrix Editor" in response.text
    assert "Example Farm" in response.text


def test_listing_tags_load_error_503(monkeypatch):
    async def fake_list_listing_tag_matrix(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        include_inactive_tags=False,
    ):
        raise PlatformApiError(503, "database_unavailable", "database_unavailable")

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_matrix",
        fake_list_listing_tag_matrix,
    )
    response = client.get("/listing-tags")
    assert response.status_code == 200
    assert "database_unavailable: listing tag matrix service unavailable." in response.text


def test_listing_tags_page_shows_related_api_logs(monkeypatch):
    _mock_listing_tag_matrix(monkeypatch)
    api_log_store.add(
        {
            "started_at_utc": "2026-03-25T07:10:00+00:00",
            "finished_at_utc": "2026-03-25T07:10:00+00:00",
            "method": "GET",
            "path": "/v1/admin/listing-tag-matrix",
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
    assert "/v1/admin/listing-tag-matrix" in response.text
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


def test_listing_tags_editor_preselects_existing_assignment(monkeypatch):
    _mock_listing_tag_matrix(monkeypatch)
    response = client.get("/listing-tags?selected_listing_id=listing-1")
    assert response.status_code == 200
    assert 'name="selected_tags__listing-1"' in response.text
    assert "Example Farm" in response.text
    assert 'name="selected_tags__listing-1"' in response.text
    assert 'value="microgreens"' in response.text


def test_apply_listing_tag_matrix_updates_only_changed_rows(monkeypatch):
    async def fake_list_listing_tag_matrix(
        listing_name="",
        tag_name="",
        page=1,
        page_size=25,
        include_inactive_tags=False,
    ):
        return {
            "tags": [
                {"tag_code": "microgreens", "tag_name": "Microgreens", "is_active": True},
                {"tag_code": "flowers", "tag_name": "Flowers", "is_active": True},
            ],
            "items": [
                {
                    "listing_id": "listing-1",
                    "display_name": "Example Farm",
                    "assigned_tag_codes": ["microgreens"],
                },
                {
                    "listing_id": "listing-2",
                    "display_name": "Beta Farm",
                    "assigned_tag_codes": [],
                },
            ],
            "page": page,
            "page_size": page_size,
            "total": 2,
        }

    captured = {"updates": None}

    async def fake_apply_listing_tag_matrix_updates(requested_by, reason_code, updates):
        captured["updates"] = updates
        assert requested_by == "admin@smallfarms"
        assert reason_code == "ADMIN_TAXONOMY_UPDATE"
        return {
            "total_rows": len(updates),
            "success_count": 1,
            "failure_count": 0,
            "results": [
                {
                    "listing_id": "listing-1",
                    "status": "updated",
                    "tag_codes": ["flowers", "microgreens"],
                }
            ],
        }

    monkeypatch.setattr(
        deps.platform_client,
        "list_listing_tag_matrix",
        fake_list_listing_tag_matrix,
    )
    monkeypatch.setattr(
        deps.platform_client,
        "apply_listing_tag_matrix_updates",
        fake_apply_listing_tag_matrix_updates,
    )

    response = client.post(
        "/listing-tags/matrix",
        data={
            "listing_ids": ["listing-1", "listing-2"],
            "original_tags__listing-1": "microgreens",
            "original_tags__listing-2": "",
            "selected_tags__listing-1": ["microgreens", "flowers"],
            "selected_tags__listing-2": [],
            "reason_code": "ADMIN_TAXONOMY_UPDATE",
            "requested_by": "admin@smallfarms",
            "page": "1",
            "page_size": "25",
            "listing_name": "",
            "tag_name": "",
        },
    )

    assert response.status_code == 200
    assert captured["updates"] == [{"listing_id": "listing-1", "tag_codes": ["flowers", "microgreens"]}]
