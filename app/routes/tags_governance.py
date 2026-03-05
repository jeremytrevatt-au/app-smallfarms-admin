import json

from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _render_tags(
    request: Request,
    message: str = "",
    level: str = "success",
    requested_by: str = "",
    tags_json: str = '[\n  {"tag_code": "microgreens", "tag_label": "Microgreens", "is_active": true}\n]',
    result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="tags_governance.html",
        context={
            "active_page": "tags",
            "message": message,
            "level": level,
            "requested_by": requested_by,
            "tags_json": tags_json,
            "result": result or {},
        },
    )


def _tag_error_message(exc: PlatformApiError) -> str:
    if exc.status_code == 422:
        return "validation_failed: check requested_by and canonical tag payload."
    if exc.status_code == 503:
        return "database_unavailable: tag governance service unavailable."
    return f"Tag governance failed: {exc.message}"


@router.get("/tags", include_in_schema=False)
async def tags_page(request: Request):
    return _render_tags(request)


@router.post("/tags", include_in_schema=False)
async def upsert_tags(
    request: Request,
    requested_by: str = Form(""),
    tags_json: str = Form(""),
):
    if not requested_by.strip():
        return _render_tags(
            request,
            "requested_by is required.",
            "error",
            requested_by=requested_by,
            tags_json=tags_json,
        )

    try:
        parsed_tags = json.loads(tags_json)
    except json.JSONDecodeError:
        return _render_tags(
            request,
            "tags payload must be valid JSON array.",
            "error",
            requested_by=requested_by,
            tags_json=tags_json,
        )

    if not isinstance(parsed_tags, list):
        return _render_tags(
            request,
            "tags payload must be a JSON array.",
            "error",
            requested_by=requested_by,
            tags_json=tags_json,
        )

    try:
        result = await platform_client.upsert_tags(requested_by, parsed_tags)
        return _render_tags(
            request,
            "Canonical tags updated.",
            "success",
            requested_by=requested_by,
            tags_json=tags_json,
            result=result,
        )
    except PlatformApiError as exc:
        return _render_tags(
            request,
            _tag_error_message(exc),
            "error",
            requested_by=requested_by,
            tags_json=tags_json,
        )
