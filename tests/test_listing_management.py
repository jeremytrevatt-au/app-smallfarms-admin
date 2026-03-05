from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_listing_management_page_loads():
    response = client.get("/listings/manage")
    assert response.status_code == 200
    assert "Listing Lifecycle Management" in response.text
    assert "Patch Listing Metadata" in response.text
    assert "Delete Listing (Soft-Delete)" in response.text


def test_patch_listing_success(monkeypatch):
    captured = {"payload": None}

    async def fake_patch_admin_listing(
        listing_id, requested_by, reason_code, display_name, primary_category_code, status_code
    ):
        captured["payload"] = {
            "listing_id": listing_id,
            "requested_by": requested_by,
            "reason_code": reason_code,
            "display_name": display_name,
            "primary_category_code": primary_category_code,
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
            "primary_category_code": "",
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
            "primary_category_code": "",
            "status_code": "",
        },
    )

    assert response.status_code == 200
    assert (
        "At least one mutable field is required: display_name, primary_category_code, or status_code."
        in response.text
    )


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
