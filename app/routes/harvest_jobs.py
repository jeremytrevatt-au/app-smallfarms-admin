import json
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request

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
        return _render_harvest(
            request,
            _with_timestamp("Harvest preview completed. Select candidates for import."),
            "success",
            harvest_result=harvest_result,
        )
    except PlatformApiError as exc:
        return _render_harvest(request, _with_timestamp(f"Harvest job failed: {exc.message}"), "error")


@router.post("/places/import/dry-run", include_in_schema=False)
async def import_places_dry_run(request: Request, payload_json: str = Form("")):
    return await _run_places_import(request, payload_json, dry_run=True)


@router.post("/places/import/commit", include_in_schema=False)
async def import_places_commit(request: Request, payload_json: str = Form("")):
    return await _run_places_import(request, payload_json, dry_run=False)


async def _run_places_import(request: Request, payload_json: str, dry_run: bool):
    if not payload_json.strip():
        return _render_harvest(
            request,
            "Import payload JSON is required.",
            "error",
            payload_text=payload_json,
        )

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return _render_harvest(
            request,
            "Import payload must be valid JSON.",
            "error",
            payload_text=payload_json,
        )

    if not isinstance(payload, dict):
        return _render_harvest(
            request,
            "Import payload must be a JSON object.",
            "error",
            payload_text=payload_json,
        )

    try:
        result = await platform_client.import_places(payload, dry_run=dry_run)
        inserted_count = result.get("inserted_count", 0)
        updated_count = result.get("updated_count", 0)
        outcomes = result.get("outcomes", [])
        mode = "true" if dry_run else "false"
        message = (
            f"dry_run={mode} import completed: inserted_count={inserted_count}, "
            f"updated_count={updated_count}, outcomes={outcomes}"
        )
        return _render_harvest(
            request,
            _with_timestamp(message),
            "success",
            payload_text=payload_json,
            import_result=result,
        )
    except PlatformApiError as exc:
        return _render_harvest(
            request,
            _with_timestamp(_import_error_message(exc)),
            "error",
            payload_text=payload_json,
        )
