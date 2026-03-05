import json

from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.models.forms import HarvestJobForm
from app.services.platform_api import PlatformApiError
from pydantic import ValidationError


router = APIRouter()


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
async def create_harvest_job(request: Request, source: str = Form(""), note: str = Form("")):
    try:
        form = HarvestJobForm(source=source, note=note)
    except ValidationError:
        return _render_harvest(request, "source is required.", "error")

    try:
        harvest_result = await platform_client.create_harvest_job(form.source, form.note)
        return _render_harvest(
            request,
            "Harvest preview completed. Select candidates for import.",
            "success",
            harvest_result=harvest_result,
        )
    except PlatformApiError as exc:
        return _render_harvest(request, f"Harvest job failed: {exc.message}", "error")


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
            message,
            "success",
            payload_text=payload_json,
            import_result=result,
        )
    except PlatformApiError as exc:
        return _render_harvest(
            request,
            _import_error_message(exc),
            "error",
            payload_text=payload_json,
        )
