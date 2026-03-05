import json
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import platform_client, templates
from app.models.forms import HarvestJobForm
from app.services.platform_api import PlatformApiError
from pydantic import ValidationError


router = APIRouter()


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _with_timestamp(message: str) -> str:
    return f"{message} (at {_utc_now_label()})"


def _render_harvest(
    request: Request,
    message: str = "",
    level: str = "success",
    payload_text: str = '{\n  "candidates": []\n}',
    harvest_result: dict | None = None,
    import_result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="harvest.html",
        context={
            "active_page": "harvest",
            "message": message,
            "level": level,
            "payload_text": payload_text,
            "harvest_result": harvest_result or {},
            "import_result": import_result or {},
        },
    )


def _redirect_harvest(message: str, level: str = "success") -> RedirectResponse:
    from urllib.parse import urlencode

    query = urlencode({"message": message, "level": level})
    return RedirectResponse(url=f"/harvest?{query}", status_code=303)


def _sort_preview_results(harvest_result: dict) -> dict:
    items = harvest_result.get("preview_results")
    if not isinstance(items, list):
        return harvest_result
    sorted_items = sorted(items, key=lambda x: str(x.get("name", "")).lower())
    updated = dict(harvest_result)
    updated["preview_results"] = sorted_items
    updated["preview_result_count"] = len(sorted_items)
    return updated


def _sanitize_import_payload(payload: dict) -> tuple[dict, list[str]]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return payload, []

    sanitized_candidates: list[dict] = []
    partial_location_removed_ids: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            sanitized_candidates.append(item)
            continue

        candidate = dict(item)
        location = candidate.get("location")
        if isinstance(location, dict):
            has_lat = location.get("lat") is not None
            has_lng = location.get("lng") is not None
            if has_lat and has_lng:
                pass
            elif has_lat or has_lng:
                candidate.pop("location", None)
                provider_id = str(candidate.get("provider_place_id", "unknown"))
                partial_location_removed_ids.append(provider_id)
        sanitized_candidates.append(candidate)

    updated = dict(payload)
    updated["candidates"] = sanitized_candidates
    return updated, partial_location_removed_ids


def _shape_import_payload(payload: dict) -> dict:
    shaped = dict(payload)
    candidates = shaped.get("candidates")
    if not isinstance(candidates, list):
        return shaped

    mapped_candidates: list[dict] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        candidate = dict(item)
        if not candidate.get("display_name"):
            candidate["display_name"] = candidate.get("name", "")
        candidate.pop("exists_in_database", None)
        candidate.pop("existing_listing_id", None)
        mapped_candidates.append(candidate)

    shaped["candidates"] = mapped_candidates
    return shaped


def _validate_import_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    if not str(payload.get("requested_by", "")).strip():
        errors.append("missing top-level field: requested_by")
    if not str(payload.get("target_tenant_code", "")).strip():
        errors.append("missing top-level field: target_tenant_code")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("missing candidates[]")
        return errors

    for idx, item in enumerate(candidates):
        if not isinstance(item, dict):
            errors.append(f"candidate[{idx}] is not an object")
            continue
        provider_id = item.get("provider_place_id", f"index-{idx}")
        if not str(item.get("display_name", "")).strip():
            errors.append(f"candidate {provider_id}: missing display_name")
        if not str(item.get("provider_place_id", "")).strip():
            errors.append(f"candidate {provider_id}: missing provider_place_id")
    return errors


def _import_error_message(exc: PlatformApiError) -> str:
    if exc.status_code == 422:
        return "validation_failed: partial location payload is invalid."
    if exc.status_code == 503:
        return "database_unavailable: import service unavailable. Retry after backend recovery."
    return f"Places import failed: {exc.message}"


@router.get("/harvest", include_in_schema=False)
async def harvest_page(request: Request, message: str = "", level: str = "success"):
    return _render_harvest(request, message, level)


@router.post("/harvest/jobs", include_in_schema=False)
async def create_harvest_job(
    request: Request,
    query_text: str = Form(""),
    note: str = Form(""),
    search_scope: str = Form(""),
    region_hint: str = Form(""),
    category_codes_csv: str = Form(""),
    max_requests: str = Form(""),
    max_runtime_minutes: str = Form(""),
    priority_code: str = Form(""),
    requested_by: str = Form(""),
):
    if (
        not query_text.strip()
        or not search_scope.strip()
        or not category_codes_csv.strip()
        or not max_requests.strip()
        or not max_runtime_minutes.strip()
        or not priority_code.strip()
        or not requested_by.strip()
    ):
        return _render_harvest(
            request,
            _with_timestamp(
                "Harvest request is invalid. Required: query_text, search_scope, category_codes, "
                "max_requests, max_runtime_minutes, priority_code, requested_by."
            ),
            "error",
        )

    category_codes = [item.strip() for item in category_codes_csv.split(",") if item.strip()]
    try:
        form = HarvestJobForm(
            query_text=query_text,
            note=note,
            search_scope=search_scope,
            region_hint=region_hint,
            category_codes=category_codes,
            max_requests=int(max_requests),
            max_runtime_minutes=int(max_runtime_minutes),
            priority_code=priority_code,
            requested_by=requested_by,
        )
    except ValidationError:
        return _render_harvest(
            request,
            _with_timestamp(
                "Harvest request is invalid. Required: query_text, search_scope, category_codes, "
                "max_requests, max_runtime_minutes, priority_code, requested_by."
            ),
            "error",
        )
    except ValueError:
        return _render_harvest(
            request,
            _with_timestamp("max_requests and max_runtime_minutes must be numeric."),
            "error",
        )

    try:
        payload = {
            "query_text": form.query_text,
            "note": form.note,
            "search_scope": form.search_scope,
            "category_codes": form.category_codes,
            "max_requests": form.max_requests,
            "max_runtime_minutes": form.max_runtime_minutes,
            "priority_code": form.priority_code,
            "requested_by": form.requested_by,
        }
        if form.region_hint.strip():
            payload["region_hint"] = form.region_hint.strip()
        harvest_result = await platform_client.create_harvest_job(payload)
        harvest_result = _sort_preview_results(harvest_result)
        return _render_harvest(
            request,
            _with_timestamp("Harvest preview completed. Select candidates for import."),
            "success",
            harvest_result=harvest_result,
        )
    except PlatformApiError as exc:
        return _render_harvest(request, _with_timestamp(f"Harvest job failed: {exc.message}"), "error")


@router.post("/places/import/dry-run", include_in_schema=False)
async def import_places_dry_run(
    request: Request,
    payload_json: str = Form(""),
    import_requested_by: str = Form(""),
    import_target_tenant_code: str = Form(""),
):
    return await _run_places_import(
        request,
        payload_json,
        dry_run=True,
        import_requested_by=import_requested_by,
        import_target_tenant_code=import_target_tenant_code,
    )


@router.post("/places/import/commit", include_in_schema=False)
async def import_places_commit(
    request: Request,
    payload_json: str = Form(""),
    import_requested_by: str = Form(""),
    import_target_tenant_code: str = Form(""),
):
    return await _run_places_import(
        request,
        payload_json,
        dry_run=False,
        import_requested_by=import_requested_by,
        import_target_tenant_code=import_target_tenant_code,
    )


async def _run_places_import(
    request: Request,
    payload_json: str,
    dry_run: bool,
    import_requested_by: str,
    import_target_tenant_code: str,
):
    if not import_requested_by.strip() or not import_target_tenant_code.strip():
        return _redirect_harvest(
            _with_timestamp(
                "Import request is invalid. Required: import_requested_by and import_target_tenant_code."
            ),
            "error",
        )

    if not payload_json.strip():
        return _redirect_harvest("Import payload JSON is required.", "error")

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return _redirect_harvest("Import payload must be valid JSON.", "error")

    if not isinstance(payload, dict):
        return _redirect_harvest("Import payload must be a JSON object.", "error")

    if import_requested_by.strip() and "requested_by" not in payload:
        payload["requested_by"] = import_requested_by.strip()
    if import_target_tenant_code.strip() and "target_tenant_code" not in payload:
        payload["target_tenant_code"] = import_target_tenant_code.strip()

    shaped_payload = _shape_import_payload(payload)
    validation_errors = _validate_import_payload(shaped_payload)
    if validation_errors:
        return _redirect_harvest(
            _with_timestamp("Import preflight failed: " + "; ".join(validation_errors)),
            "error",
        )

    try:
        sanitized_payload, partial_location_removed_ids = _sanitize_import_payload(shaped_payload)
        result = await platform_client.import_places(sanitized_payload, dry_run=dry_run)
        inserted_count = result.get("inserted_count", 0)
        updated_count = result.get("updated_count", 0)
        outcomes = result.get("outcomes", [])
        mode = "true" if dry_run else "false"
        message = (
            f"dry_run={mode} import completed: inserted_count={inserted_count}, "
            f"updated_count={updated_count}, outcomes={outcomes}"
        )
        if partial_location_removed_ids:
            message += (
                f", partial_location_removed={len(partial_location_removed_ids)} "
                f"provider_place_ids={partial_location_removed_ids}"
            )
        return _redirect_harvest(_with_timestamp(message), "success")
    except PlatformApiError as exc:
        return _redirect_harvest(_with_timestamp(_import_error_message(exc)), "error")
