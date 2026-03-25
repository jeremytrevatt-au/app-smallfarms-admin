import json

from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_tag_rows(response: dict) -> list[dict]:
    raw = response.get("items")
    if not isinstance(raw, list):
        raw = response.get("tags")
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = str(item.get("tag_code") or item.get("code") or "").strip()
        label = str(item.get("tag_label") or item.get("tag_name") or item.get("label") or "").strip()
        if not code:
            continue
        rows.append(
            {
                "tag_code": code,
                "tag_label": label or code,
                "is_active": bool(item.get("is_active", True)),
            }
        )
    rows.sort(key=lambda row: row["tag_code"].lower())
    return rows


def _rows_to_json_text(rows: list[dict]) -> str:
    return json.dumps(rows, indent=2)


def _filter_tag_rows(rows: list[dict], tag_name: str) -> list[dict]:
    if not tag_name.strip():
        return rows
    needle = tag_name.strip().lower()
    return [
        row
        for row in rows
        if needle in row["tag_code"].lower() or needle in row["tag_label"].lower()
    ]


def _parse_rows_from_form(request_form) -> list[dict]:
    row_ids = [str(item).strip() for item in request_form.getlist("row_ids") if str(item).strip()]
    rows: list[dict] = []
    for row_id in row_ids:
        code = str(request_form.get(f"tag_code__{row_id}") or "").strip()
        label = str(request_form.get(f"tag_label__{row_id}") or "").strip()
        is_active = _parse_bool(str(request_form.get(f"is_active__{row_id}") or ""), False)
        if not code:
            continue
        rows.append(
            {
                "tag_code": code,
                "tag_label": label or code,
                "is_active": is_active,
            }
        )
    return rows


def _render_tags(
    request: Request,
    message: str = "",
    level: str = "success",
    requested_by: str = "",
    tag_name: str = "",
    tag_rows: list[dict] | None = None,
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
            "tag_name": tag_name,
            "tag_rows": tag_rows or [],
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
    tag_name = (request.query_params.get("tag_name") or "").strip()
    message = ""
    level = "success"
    rows: list[dict] = []
    try:
        rows = _normalize_tag_rows(await platform_client.list_canonical_tags())
    except PlatformApiError as exc:
        message = _tag_error_message(exc)
        level = "error"

    filtered_rows = _filter_tag_rows(rows, tag_name)
    return _render_tags(
        request,
        message=message,
        level=level,
        tag_name=tag_name,
        tag_rows=filtered_rows,
        tags_json=_rows_to_json_text(filtered_rows or rows),
    )


@router.post("/tags", include_in_schema=False)
async def upsert_tags(
    request: Request,
    requested_by: str = Form(""),
    tag_name: str = Form(""),
    tags_json: str = Form(""),
):
    if not requested_by.strip():
        return _render_tags(
            request,
            "requested_by is required.",
            "error",
            requested_by=requested_by,
            tag_name=tag_name,
            tags_json=tags_json,
        )

    form = await request.form()
    parsed_tags = _parse_rows_from_form(form)
    if not parsed_tags and tags_json.strip():
        try:
            parsed_json = json.loads(tags_json)
        except json.JSONDecodeError:
            return _render_tags(
                request,
                "tags payload must be valid JSON array.",
                "error",
                requested_by=requested_by,
                tag_name=tag_name,
                tags_json=tags_json,
            )
        if not isinstance(parsed_json, list):
            return _render_tags(
                request,
                "tags payload must be a JSON array.",
                "error",
                requested_by=requested_by,
                tag_name=tag_name,
                tags_json=tags_json,
            )
        parsed_tags = [row for row in parsed_json if isinstance(row, dict)]

    try:
        result = await platform_client.upsert_tags(requested_by, parsed_tags)
        fresh_rows: list[dict] = []
        try:
            fresh_rows = _normalize_tag_rows(await platform_client.list_canonical_tags())
        except PlatformApiError:
            fresh_rows = parsed_tags
        filtered_rows = _filter_tag_rows(fresh_rows, tag_name)
        return _render_tags(
            request,
            "Canonical tags updated.",
            "success",
            requested_by=requested_by,
            tag_name=tag_name,
            tag_rows=filtered_rows,
            tags_json=_rows_to_json_text(filtered_rows or fresh_rows),
            result=result,
        )
    except PlatformApiError as exc:
        fallback_rows = _filter_tag_rows(
            _parse_rows_from_form(form) or _filter_tag_rows([], tag_name),
            tag_name,
        )
        return _render_tags(
            request,
            _tag_error_message(exc),
            "error",
            requested_by=requested_by,
            tag_name=tag_name,
            tag_rows=fallback_rows,
            tags_json=tags_json or _rows_to_json_text(fallback_rows),
        )
