from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_listing_management_page_loads(monkeypatch):
    async def fake_list_admin_listings(listing_name="", page=1, page_size=25):
        return {
            "items": [
                {"listing_id": "listing-123", "listing_name": "Example Farm", "status_code": "active"},
            ],
            "page": page,
            "page_size": page_size,
            "total": 1,
        }

    monkeypatch.setattr(deps.platform_client, "list_admin_listings", fake_list_admin_listings)
    response = client.get("/listings/manage")
    assert response.status_code == 200
    assert "Listing Lifecycle Management" in response.text
    assert "Listing Row Grid" in response.text
    assert "Apply Grid Changes" in response.text


def test_patch_listing_success(monkeypatch):
    captured = {"payload": None}

    async def fake_patch_admin_listing(listing_id, requested_by, reason_code, display_name, status_code):
        captured["payload"] = {
            "listing_id": listing_id,
            "requested_by": requested_by,
            "reason_code": reason_code,
            "display_name": display_name,
            "status_code": status_code,
        }
        return {"listing_id": listing_id, "status_code": status_code}

    monkeypatch.setattr(deps.platform_client, "patch_admin_listing", fake_patch_admin_listing)

    response = client.post(
        "/listings/manage/update",
        data={
            "listing_id": "listing-123",
            "requested_by": "admin@smallfarms.com.au",
            "reason_code": "ADMIN_LISTING_UPDATE",
            "display_name": "Example Farm",
            "status_code": "active",
        },
    )

    assert response.status_code == 200
    assert "Listing updated." in response.text
    assert captured["payload"] is not None
    assert captured["payload"]["listing_id"] == "listing-123"
    assert captured["payload"]["status_code"] == "active"


def test_patch_listing_requires_mutable_field():
    response = client.post(
        "/listings/manage/update",
        data={
            "listing_id": "listing-123",
            "requested_by": "admin@smallfarms.com.au",
            "reason_code": "ADMIN_LISTING_UPDATE",
            "display_name": "",
            "status_code": "",
        },
    )

    assert response.status_code == 200
    assert "At least one mutable field is required: display_name or status_code." in response.text


def test_patch_listing_does_not_send_primary_category_code(monkeypatch):
    captured = {"payload": None}

    async def fake_patch_admin_listing(listing_id, requested_by, reason_code, display_name, status_code):
        captured["payload"] = {
            "listing_id": listing_id,
            "requested_by": requested_by,
            "reason_code": reason_code,
            "display_name": display_name,
            "status_code": status_code,
        }
        return {"listing_id": listing_id, "status_code": status_code}

    monkeypatch.setattr(deps.platform_client, "patch_admin_listing", fake_patch_admin_listing)

    response = client.post(
        "/listings/manage/update",
        data={
            "listing_id": "listing-456",
            "requested_by": "admin@smallfarms.com.au",
            "reason_code": "ADMIN_LISTING_UPDATE",
            "display_name": "Only Name",
            "primary_category_code": "should-be-ignored",
            "status_code": "",
        },
    )

    assert response.status_code == 200
    assert captured["payload"] is not None
    assert "primary_category_code" not in captured["payload"]


def test_delete_listing_success(monkeypatch):
    async def fake_delete_admin_listing(listing_id, requested_by, reason_code):
        return {
            "listing_id": listing_id,
            "status_code": "deleted",
            "requested_by": requested_by,
            "reason_code": reason_code,
        }

    monkeypatch.setattr(deps.platform_client, "delete_admin_listing", fake_delete_admin_listing)

    response = client.post(
        "/listings/manage/delete",
        data={
            "listing_id": "listing-123",
            "requested_by": "admin@smallfarms.com.au",
            "reason_code": "ADMIN_LISTING_DELETE",
        },
    )

    assert response.status_code == 200
    assert "Listing deleted (soft-delete)." in response.text


def test_delete_listing_not_found(monkeypatch):
    async def fake_delete_admin_listing(listing_id, requested_by, reason_code):
        raise PlatformApiError(404, "listing_not_found", "listing_not_found")

    monkeypatch.setattr(deps.platform_client, "delete_admin_listing", fake_delete_admin_listing)

    response = client.post(
        "/listings/manage/delete",
        data={
            "listing_id": "missing-id",
            "requested_by": "admin@smallfarms.com.au",
            "reason_code": "ADMIN_LISTING_DELETE",
        },
    )

    assert response.status_code == 200
    assert "listing_not_found: listing_id does not exist." in response.text


def test_listing_management_grid_apply_updates_changed_rows(monkeypatch):
    async def fake_list_admin_listings(listing_name="", page=1, page_size=25):
        return {
            "items": [
                {"listing_id": "listing-1", "listing_name": "Example Farm", "status_code": "active"},
                {"listing_id": "listing-2", "listing_name": "Beta Farm", "status_code": "pending"},
            ],
            "page": page,
            "page_size": page_size,
            "total": 2,
        }

    patched = []
    deleted = []

    async def fake_patch_admin_listing(listing_id, requested_by, reason_code, display_name, status_code):
        patched.append((listing_id, requested_by, reason_code, display_name, status_code))
        return {"listing_id": listing_id}

    async def fake_delete_admin_listing(listing_id, requested_by, reason_code):
        deleted.append((listing_id, requested_by, reason_code))
        return {"listing_id": listing_id}

    monkeypatch.setattr(deps.platform_client, "list_admin_listings", fake_list_admin_listings)
    monkeypatch.setattr(deps.platform_client, "patch_admin_listing", fake_patch_admin_listing)
    monkeypatch.setattr(deps.platform_client, "delete_admin_listing", fake_delete_admin_listing)

    response = client.post(
        "/listings/manage/matrix",
        data={
            "listing_ids": ["listing-1", "listing-2"],
            "original_display_name__listing-1": "Example Farm",
            "original_status_code__listing-1": "active",
            "display_name__listing-1": "Example Farm Updated",
            "status_code__listing-1": "active",
            "delete__listing-1": "",
            "original_display_name__listing-2": "Beta Farm",
            "original_status_code__listing-2": "pending",
            "display_name__listing-2": "Beta Farm",
            "status_code__listing-2": "pending",
            "delete__listing-2": "true",
            "matrix_requested_by": "admin@smallfarms.com.au",
            "matrix_reason_code": "ADMIN_LISTING_UPDATE",
            "matrix_delete_enabled": "true",
            "listing_name": "",
            "page": "1",
            "page_size": "25",
        },
    )

    assert response.status_code == 200
    assert len(patched) == 1
    assert patched[0][0] == "listing-1"
    assert patched[0][3] == "Example Farm Updated"
    assert len(deleted) == 1
    assert deleted[0][0] == "listing-2"
