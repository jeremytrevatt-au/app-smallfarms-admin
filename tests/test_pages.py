from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_moderation_page_loads(monkeypatch):
    async def fake_list_submissions(status=None, page=None, page_size=None):
        return {
            "items": [
                {
                    "submission_id": "sub-123",
                    "listing_id": "listing-123",
                    "status_code": "submitted_pending_review",
                    "submitted_by_member_id": "member-123",
                    "submitted_at": "2026-03-23T01:14:24",
                    "submission_payload": {
                        "draft_id": "draft-123",
                        "submission_note": "first note",
                        "preview_html": "<section><h1>Preview</h1><p>Safe paragraph</p></section>",
                        "auto_approved_after_initial_moderation": False,
                    },
                }
            ],
            "page": 1,
            "page_size": 25,
            "total": 1,
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Moderation Queue" in response.text
    assert "Submission sub-123" in response.text
    assert "Listing ID: listing-123" in response.text
    assert "submitted_pending_review" in response.text
    assert "Draft ID: draft-123" in response.text
    assert "Submission Note: first note" in response.text
    assert "Auto-approved after initial moderation:" in response.text
    assert "Pending queue" in response.text
    assert "View auto-approved" in response.text
    assert "Submission Preview sub-123" in response.text


def test_moderation_page_renders_payload_defaults(monkeypatch):
    async def fake_list_submissions(status=None, page=None, page_size=None):
        return {
            "items": [
                {
                    "submission_id": "sub-456",
                    "listing_id": "listing-456",
                    "status_code": "submitted_pending_review",
                    "submitted_by_member_id": "member-456",
                    "submitted_at": "2026-03-23T01:14:24",
                    "submission_payload": {},
                }
            ],
            "page": 1,
            "page_size": 25,
            "total": 1,
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation")
    assert response.status_code == 200
    assert "Draft ID: -" in response.text
    assert "Submission Note: -" in response.text
    assert "No HTML preview provided." in response.text


def test_moderation_page_hides_manual_actions_for_auto_approved_status(monkeypatch):
    async def fake_list_submissions(status=None, page=None, page_size=None):
        return {
            "items": [
                {
                    "submission_id": "sub-auto",
                    "listing_id": "listing-auto",
                    "status_code": "approved_pending_publish",
                    "submitted_by_member_id": "member-789",
                    "submitted_at": "2026-03-23T02:52:00",
                    "submission_payload": {
                        "draft_id": "draft-auto",
                        "auto_approved_after_initial_moderation": True,
                    },
                }
            ],
            "page": 1,
            "page_size": 25,
            "total": 1,
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation?status=approved_pending_publish")
    assert response.status_code == 200
    assert "No manual moderation required for this status." in response.text
    assert "auto_approved_after_initial_moderation" not in response.text
    assert "Approve" not in response.text
    assert "Reject" not in response.text


def test_moderation_page_forwards_filters_and_pagination(monkeypatch):
    seen: dict[str, object] = {}

    async def fake_list_submissions(status=None, page=None, page_size=None):
        seen["status"] = status
        seen["page"] = page
        seen["page_size"] = page_size
        return {"items": [], "page": page or 1, "page_size": page_size or 25, "total": 0}

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation?status=submitted_pending_review&page=2&page_size=10")
    assert response.status_code == 200
    assert seen["status"] == "submitted_pending_review"
    assert seen["page"] == 2
    assert seen["page_size"] == 10
    assert "Page 2 of 1 | Total matching submissions: 0" in response.text


def test_moderation_page_clamps_invalid_pagination(monkeypatch):
    seen: dict[str, object] = {}

    async def fake_list_submissions(status=None, page=None, page_size=None):
        seen["status"] = status
        seen["page"] = page
        seen["page_size"] = page_size
        return {
            "items": [],
            "page": page or 1,
            "page_size": page_size or 25,
            "total": 0,
        }

    monkeypatch.setattr(deps.platform_client, "list_submissions", fake_list_submissions)
    response = client.get("/moderation?status=&page=0&page_size=999")
    assert response.status_code == 200
    assert seen["status"] == "submitted_pending_review"
    assert seen["page"] == 1
    assert seen["page_size"] == 100


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
