from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.api_log_store import api_log_store
from app.services.platform_api import PlatformApiError


router = APIRouter()


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _parse_int(value: str | None, default: int, minimum: int, maximum: int | None = None) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    if parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _render_listing_tags(
    request: Request,
    message: str = "",
    level: str = "success",
    listing_name: str = "",
    tag_name: str = "",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    total: int = 0,
    total_pages: int = 1,
    group_by_listing: bool = False,
    items: list[dict] | None = None,
    grouped_items: list[dict] | None = None,
    listing_options: list[dict] | None = None,
    canonical_tags: list[dict] | None = None,
    selected_listing_id: str = "",
    selected_listing_name: str = "",
    selected_listing_tag_codes: list[str] | None = None,
    api_log_items: list[dict] | None = None,
    listing_id: str = "",
    tag_codes_csv: str = "",
    reason_code: str = "",
    requested_by: str = "",
    result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="listing_tag_assignments.html",
        context={
            "active_page": "listing-tags",
            "message": message,
            "level": level,
            "listing_name": listing_name,
            "tag_name": tag_name,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "group_by_listing": group_by_listing,
            "items": items or [],
            "grouped_items": grouped_items or [],
            "listing_options": listing_options or [],
            "canonical_tags": canonical_tags or [],
            "selected_listing_id": selected_listing_id,
            "selected_listing_name": selected_listing_name,
            "selected_listing_tag_codes": selected_listing_tag_codes or [],
            "api_log_items": api_log_items or [],
            "has_prev_page": page > 1,
            "has_next_page": page < total_pages,
            "prev_page": page - 1 if page > 1 else 1,
            "next_page": page + 1 if page < total_pages else total_pages,
            "listing_id": listing_id,
            "tag_codes_csv": tag_codes_csv,
            "reason_code": reason_code,
            "requested_by": requested_by,
            "result": result or {},
        },
    )


def _assignment_error_message(exc: PlatformApiError) -> str:
    if exc.status_code == 422:
        return "validation_failed: one or more tag codes are unknown or inactive."
    if exc.status_code == 503:
        return "database_unavailable: listing tag assignment service unavailable."
    return f"Tag assignment failed: {exc.message}"


def _tag_catalog_error_message(exc: PlatformApiError) -> str:
    if exc.status_code == 503:
        return "database_unavailable: canonical tag catalog unavailable."
    if exc.status_code == 404:
        return "Tag catalog endpoint not found. Confirm GET /v1/admin/tags is deployed."
    return f"Failed to load canonical tags: {exc.message}"


def _normalize_canonical_tags(response: dict) -> list[dict]:
    raw = response.get("items")
    if not isinstance(raw, list):
        raw = response.get("tags")
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("tag_code") or entry.get("code") or "").strip()
        name = str(entry.get("tag_name") or entry.get("tag_label") or entry.get("label") or "").strip()
        if not code:
            continue
        normalized.append(
            {
                "tag_code": code,
                "tag_name": name or code,
                "is_active": bool(entry.get("is_active", True)),
            }
        )
    normalized.sort(key=lambda item: item["tag_name"].lower())
    return normalized


def _listing_options_from_grouped(grouped_items: list[dict]) -> list[dict]:
    options: list[dict] = []
    for entry in grouped_items:
        listing_id = str(entry.get("listing_id") or "").strip()
        if not listing_id:
            continue
        tags_raw = entry.get("tags")
        selected_codes: list[str] = []
        if isinstance(tags_raw, list):
            for tag in tags_raw:
                if not isinstance(tag, dict):
                    continue
                code = str(tag.get("tag_code") or "").strip()
                if code:
                    selected_codes.append(code)
        options.append(
            {
                "listing_id": listing_id,
                "listing_name": str(entry.get("listing_name") or listing_id),
                "latest_assigned_at": str(entry.get("latest_assigned_at") or ""),
                "selected_tag_codes": selected_codes,
            }
        )
    return options


def _listing_tag_api_logs(limit: int = 50) -> list[dict]:
    matched: list[dict] = []
    for entry in api_log_store.list_newest_first():
        path = str(entry.get("path", ""))
        if (
            "/v1/admin/listing-tag-assignments" in path
            or "/v1/admin/listings/" in path
            and "/tag-assignments" in path
        ):
            matched.append(entry)
        if len(matched) >= limit:
            break
    return matched


@router.get("/listing-tags", include_in_schema=False)
async def listing_tags_page(request: Request):
    listing_name = (request.query_params.get("listing_name") or "").strip()
    tag_name = (request.query_params.get("tag_name") or "").strip()
    selected_listing_id = (request.query_params.get("selected_listing_id") or "").strip()
    page = _parse_int(request.query_params.get("page"), DEFAULT_PAGE, 1)
    page_size = _parse_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    group_by_listing = _parse_bool(request.query_params.get("group_by_listing"), False)

    items: list[dict] = []
    grouped_items: list[dict] = []
    listing_options: list[dict] = []
    canonical_tags: list[dict] = []
    selected_listing_name = ""
    selected_listing_tag_codes: list[str] = []
    total = 0
    response_page = page
    response_page_size = page_size
    message = ""
    level = "success"
    try:
        response = await platform_client.list_listing_tag_assignments(
            listing_name=listing_name,
            tag_name=tag_name,
            page=page,
            page_size=page_size,
            group_by_listing=group_by_listing,
        )
        raw_items = response.get("items", [])
        if isinstance(raw_items, list):
            items = [entry for entry in raw_items if isinstance(entry, dict)]
        raw_grouped = response.get("grouped_items", [])
        if isinstance(raw_grouped, list):
            grouped_items = [entry for entry in raw_grouped if isinstance(entry, dict)]
        response_page = _parse_int(str(response.get("page")), page, 1)
        response_page_size = _parse_int(
            str(response.get("page_size")),
            page_size,
            1,
            MAX_PAGE_SIZE,
        )
        total = _parse_int(str(response.get("total")), len(items), 0)
    except PlatformApiError as exc:
        message = (
            "database_unavailable: listing tag assignment service unavailable."
            if exc.status_code == 503
            else f"Failed to load listing tag assignments: {exc.message}"
        )
        level = "error"

    try:
        listing_selector_response = await platform_client.list_listing_tag_assignments(
            listing_name=listing_name,
            tag_name="",
            page=1,
            page_size=100,
            group_by_listing=True,
        )
        selector_grouped = listing_selector_response.get("grouped_items", [])
        if isinstance(selector_grouped, list):
            listing_options = _listing_options_from_grouped(
                [entry for entry in selector_grouped if isinstance(entry, dict)]
            )
    except PlatformApiError as exc:
        if not message:
            message = (
                "database_unavailable: listing selector unavailable."
                if exc.status_code == 503
                else f"Failed to load listing selector options: {exc.message}"
            )
            level = "error"

    try:
        canonical_tags = _normalize_canonical_tags(await platform_client.list_canonical_tags())
    except PlatformApiError as exc:
        if not message:
            message = _tag_catalog_error_message(exc)
            level = "error"

    if selected_listing_id and listing_options:
        for option in listing_options:
            if option["listing_id"] == selected_listing_id:
                selected_listing_name = option["listing_name"]
                selected_listing_tag_codes = option["selected_tag_codes"]
                break

    total_pages = (
        (total + response_page_size - 1) // response_page_size if response_page_size > 0 else 1
    )
    if total_pages < 1:
        total_pages = 1
    return _render_listing_tags(
        request,
        message=message,
        level=level,
        listing_name=listing_name,
        tag_name=tag_name,
        page=response_page,
        page_size=response_page_size,
        total=total,
        total_pages=total_pages,
        group_by_listing=group_by_listing,
        items=items,
        grouped_items=grouped_items,
        listing_options=listing_options,
        canonical_tags=canonical_tags,
        selected_listing_id=selected_listing_id,
        selected_listing_name=selected_listing_name,
        selected_listing_tag_codes=selected_listing_tag_codes,
        api_log_items=_listing_tag_api_logs(),
    )


@router.post("/listing-tags", include_in_schema=False)
async def replace_listing_tags(
    request: Request,
    listing_id: str = Form(""),
    tag_codes: list[str] = Form([]),
    tag_codes_csv: str = Form(""),
    reason_code: str = Form(""),
    requested_by: str = Form(""),
):
    parsed_tag_codes = [item.strip() for item in tag_codes if item.strip()]
    if not parsed_tag_codes and tag_codes_csv.strip():
        parsed_tag_codes = [item.strip() for item in tag_codes_csv.split(",") if item.strip()]
    if not listing_id.strip() or not reason_code.strip() or not requested_by.strip():
        return _render_listing_tags(
            request,
            "listing_id, reason_code, and requested_by are required.",
            "error",
            listing_id=listing_id,
            tag_codes_csv=tag_codes_csv,
            reason_code=reason_code,
            requested_by=requested_by,
            api_log_items=_listing_tag_api_logs(),
        )

    try:
        result = await platform_client.replace_listing_tag_assignments(
            listing_id=listing_id,
            tag_codes=parsed_tag_codes,
            reason_code=reason_code,
            requested_by=requested_by,
        )
        return _render_listing_tags(
            request,
            "Listing tag assignments updated.",
            "success",
            listing_id=listing_id,
            tag_codes_csv=tag_codes_csv,
            reason_code=reason_code,
            requested_by=requested_by,
            result=result,
            api_log_items=_listing_tag_api_logs(),
        )
    except PlatformApiError as exc:
        return _render_listing_tags(
            request,
            _assignment_error_message(exc),
            "error",
            listing_id=listing_id,
            tag_codes_csv=tag_codes_csv,
            reason_code=reason_code,
            requested_by=requested_by,
            api_log_items=_listing_tag_api_logs(),
        )
