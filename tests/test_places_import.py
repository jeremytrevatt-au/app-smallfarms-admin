from fastapi.testclient import TestClient

from app.main import app
from app import deps
from app.services.platform_api import PlatformApiError


client = TestClient(app)


def test_dry_run_import_success(monkeypatch):
    async def fake_import_places(_payload, dry_run):
        assert dry_run is True
        return {"inserted_count": 1, "updated_count": 0, "outcomes": ["inserted_new"]}

    monkeypatch.setattr(deps.platform_client, "import_places", fake_import_places)

    response = client.post(
        "/places/import/dry-run",
        data={"payload_json": '{"candidates": [{"external_id": "abc"}]}'},
    )

    assert response.status_code == 200
    assert "dry_run=true import completed" in response.text
    assert "inserted_new" in response.text


def test_commit_import_updated_existing(monkeypatch):
    async def fake_import_places(_payload, dry_run):
        assert dry_run is False
        return {"inserted_count": 0, "updated_count": 1, "outcomes": ["updated_existing"]}

    monkeypatch.setattr(deps.platform_client, "import_places", fake_import_places)

    response = client.post(
        "/places/import/commit",
        data={"payload_json": '{"candidates": [{"external_id": "abc"}]}'},
    )

    assert response.status_code == 200
    assert "dry_run=false import completed" in response.text
    assert "updated_existing" in response.text


def test_partial_location_returns_validation_failed(monkeypatch):
    async def fake_import_places(_payload, dry_run):
        assert dry_run is True
        raise PlatformApiError(422, "validation_failed", "validation_failed")

    monkeypatch.setattr(deps.platform_client, "import_places", fake_import_places)

    response = client.post(
        "/places/import/dry-run",
        data={"payload_json": '{"candidates": [{"location": {"lat": -33.8}}]}'},
    )

    assert response.status_code == 200
    assert "validation_failed: partial location payload is invalid." in response.text


def test_database_failure_returns_unavailable_message(monkeypatch):
    async def fake_import_places(_payload, dry_run):
        assert dry_run is False
        raise PlatformApiError(503, "database_unavailable", "database_unavailable")

    monkeypatch.setattr(deps.platform_client, "import_places", fake_import_places)

    response = client.post(
        "/places/import/commit",
        data={"payload_json": '{"candidates": [{"external_id": "abc"}]}'},
    )

    assert response.status_code == 200
    assert "database_unavailable: import service unavailable." in response.text
