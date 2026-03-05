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
        data={
            "payload_json": '{"candidates": [{"provider_place_id":"abc","display_name":"ABC"}]}',
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
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
        data={
            "payload_json": '{"candidates": [{"provider_place_id":"abc","display_name":"ABC"}]}',
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
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
        data={
            "payload_json": '{"candidates": [{"provider_place_id":"abc","display_name":"ABC","location": {"lat": -33.8}}]}',
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
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
        data={
            "payload_json": '{"candidates": [{"provider_place_id":"abc","display_name":"ABC"}]}',
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
    )

    assert response.status_code == 200
    assert "database_unavailable: import service unavailable." in response.text


def test_import_sanitizes_partial_location(monkeypatch):
    captured = {"payload": None}

    async def fake_import_places(payload, dry_run):
        assert dry_run is True
        captured["payload"] = payload
        return {"inserted_count": 0, "updated_count": 0, "outcomes": []}

    monkeypatch.setattr(deps.platform_client, "import_places", fake_import_places)

    response = client.post(
        "/places/import/dry-run",
        data={
            "payload_json": (
                '{"candidates":[{"provider_place_id":"p-1","name":"A","location":{"lat":-37.8136}},'
                '{"provider_place_id":"p-2","name":"B","location":{"lat":-37.8,"lng":144.9}}]}'
            ),
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
    )

    assert response.status_code == 200
    assert captured["payload"] is not None
    assert "location" not in captured["payload"]["candidates"][0]
    assert captured["payload"]["candidates"][1]["location"]["lat"] == -37.8
    assert captured["payload"]["candidates"][1]["location"]["lng"] == 144.9


def test_import_preflight_reports_missing_top_level_fields():
    response = client.post(
        "/places/import/commit",
        data={
            "payload_json": '{"candidates":[{"provider_place_id":"bad-1","display_name":""}]}',
            "import_requested_by": "",
            "import_target_tenant_code": "",
        },
    )

    assert response.status_code == 200
    assert "Import request is invalid. Required: import_requested_by and import_target_tenant_code." in response.text


def test_import_preflight_reports_offending_provider_ids():
    response = client.post(
        "/places/import/commit",
        data={
            "payload_json": '{"candidates":[{"provider_place_id":"bad-1","display_name":""}]}',
            "import_requested_by": "admin@smallfarms.com.au",
            "import_target_tenant_code": "naturalyield",
        },
    )

    assert response.status_code == 200
    assert "Import preflight failed:" in response.text
    assert "candidate bad-1: missing display_name" in response.text
