from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_moderation_page_loads(monkeypatch):
    async def fake_list_submissions():
        return {"items": [{"id": "sub-123", "status": "pending"}]}

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Moderation Queue" in response.text


def test_moderation_page_renders_public_read_model_defaults(monkeypatch):
    async def fake_list_submissions():
        return {
            "items": [
                {
                    "id": "sub-defaults",
                    "status": "pending",
                }
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Public Read Model Snapshot" in response.text
    assert "is_premium: false" in response.text
    assert "is_claimed: false" in response.text
    assert "Pretty Name: -" in response.text
    assert "Canonical Path: -" in response.text
    assert "Tags: []" in response.text
    assert "Location Address: -" in response.text
    assert "Website: -" in response.text
    assert "Phone: -" in response.text


def test_moderation_page_renders_contact_fields(monkeypatch):
    async def fake_list_submissions():
        return {
            "items": [
                {
                    "id": "sub-123",
                    "status": "pending",
                    "contact": {
                        "website_url": "https://examplefarm.com.au",
                        "phone_number": "+61 3 9000 0000",
                        "social_urls": {
                            "facebook": "https://facebook.com/examplefarm",
                            "instagram": None,
                        },
                    },
                }
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Contact Preview" in response.text
    assert "https://examplefarm.com.au" in response.text
    assert "+61 3 9000 0000" in response.text
    assert "https://facebook.com/examplefarm" in response.text


def test_moderation_page_renders_nullable_contact_fields(monkeypatch):
    async def fake_list_submissions():
        return {
            "items": [
                {
                    "id": "sub-456",
                    "status": "pending",
                    "contact": None,
                }
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Contact Preview" in response.text
    assert "Website: -" in response.text
    assert "Phone: -" in response.text


def test_moderation_page_renders_public_model_from_nested_listing(monkeypatch):
    async def fake_list_submissions():
        return {
            "items": [
                {
                    "id": "sub-nested",
                    "status": "pending",
                    "listing": {
                        "display_name": "Example Farm",
                        "pretty_name": "example-farm",
                        "canonical_path": "/farm/example-farm",
                        "is_premium": True,
                        "is_claimed": True,
                        "primary_category_code": "microgreens",
                        "farm_type_code": "microgreens",
                        "summary": "Premium microgreen supplier",
                        "location": {
                            "lat": -27.4705,
                            "lng": 153.0260,
                            "formatted_address": "Brisbane QLD, Australia",
                            "precision_flag": "exact",
                            "viewport_hint": {},
                        },
                        "tags": [{"code": "microgreens", "label": "Microgreens"}],
                        "contact": {
                            "website_url": "https://examplefarm.com.au",
                            "phone_number": "+61 3 9000 0000",
                            "social_urls": {},
                        },
                    },
                }
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Example Farm" in response.text
    assert "Pretty Name: example-farm" in response.text
    assert "Canonical Path: /farm/example-farm" in response.text
    assert "is_premium: true" in response.text
    assert "is_claimed: true" in response.text
    assert "microgreens" in response.text
    assert "Brisbane QLD, Australia" in response.text


def test_moderation_page_normalizes_partial_tag_entries(monkeypatch):
    async def fake_list_submissions():
        return {
            "items": [
                {
                    "id": "sub-tags",
                    "status": "pending",
                    "listing": {
                        "tags": [{"code": "flowers"}, "invalid-item"],
                    },
                }
            ]
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert '{"code": "flowers", "label": ""}' in response.text


def test_billing_page_read_only(monkeypatch):
    async def fake_subscriptions():
        return {"items": [{"tenant_id": "t-1", "status": "active"}]}

    monkeypatch.setattr(deps.platform_client, "list_billing_subscriptions", fake_subscriptions)
    response = client.get("/billing")
    assert response.status_code == 200
    assert "Manual entitlement toggles are intentionally not available" in response.text


def test_harvest_page_loads():
    response = client.get("/harvest")
    assert response.status_code == 200
    assert "Workflow: run harvest preview, dry-run import selected candidates, then commit import." in response.text


def test_api_logs_page_loads():
    response = client.get("/api-logs")
    assert response.status_code == 200
    assert "API POST Logs" in response.text


def test_header_contains_tag_nav_links():
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Tags" in response.text
    assert "Listing Tags" in response.text
    assert "Listings" in response.text
    assert "Listing Resolve" in response.text


def test_listing_management_page_loads():
    response = client.get("/listings/manage")
    assert response.status_code == 200
    assert "Listing Lifecycle Management" in response.text


def test_listing_public_resolve_page_loads():
    response = client.get("/listings/public-resolve")
    assert response.status_code == 200
    assert "Public Listing Resolve" in response.text
    assert "UUID-based listing routes remain valid and unchanged." in response.text


def test_listing_public_resolve_success(monkeypatch):
    async def fake_get_public_listing_by_pretty_name(pretty_name):
        return {
            "listing_id": "listing-123",
            "pretty_name": pretty_name,
            "canonical_path": f"/farm/{pretty_name}",
        }

    monkeypatch.setattr(
        deps.platform_client,
        "get_public_listing_by_pretty_name",
        fake_get_public_listing_by_pretty_name,
    )
    response = client.post(
        "/listings/public-resolve",
        data={"pretty_name": "example-farm"},
    )
    assert response.status_code == 200
    assert "Pretty-name lookup succeeded." in response.text
    assert "listing-123" in response.text
    assert "/farm/example-farm" in response.text


def test_listing_public_resolve_not_found(monkeypatch):
    async def fake_get_public_listing_by_pretty_name(pretty_name):
        raise PlatformApiError(404, "listing_not_found", "listing_not_found")

    monkeypatch.setattr(
        deps.platform_client,
        "get_public_listing_by_pretty_name",
        fake_get_public_listing_by_pretty_name,
    )
    response = client.post(
        "/listings/public-resolve",
        data={"pretty_name": "missing-farm"},
    )
    assert response.status_code == 200
    assert "listing_not_found: pretty_name does not exist." in response.text
