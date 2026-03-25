from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
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


@router.get("/listing-tags", include_in_schema=False)
async def listing_tags_page(request: Request):
    listing_name = (request.query_params.get("listing_name") or "").strip()
    tag_name = (request.query_params.get("tag_name") or "").strip()
    page = _parse_int(request.query_params.get("page"), DEFAULT_PAGE, 1)
    page_size = _parse_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    group_by_listing = _parse_bool(request.query_params.get("group_by_listing"), False)

    items: list[dict] = []
    grouped_items: list[dict] = []
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
    )


@router.post("/listing-tags", include_in_schema=False)
async def replace_listing_tags(
    request: Request,
    listing_id: str = Form(""),
    tag_codes_csv: str = Form(""),
    reason_code: str = Form(""),
    requested_by: str = Form(""),
):
    tag_codes = [item.strip() for item in tag_codes_csv.split(",") if item.strip()]
    if not listing_id.strip() or not reason_code.strip() or not requested_by.strip() or not tag_codes:
        return _render_listing_tags(
            request,
            "listing_id, tag_codes, reason_code, and requested_by are required.",
            "error",
            listing_id=listing_id,
            tag_codes_csv=tag_codes_csv,
            reason_code=reason_code,
            requested_by=requested_by,
        )

    try:
        result = await platform_client.replace_listing_tag_assignments(
            listing_id=listing_id,
            tag_codes=tag_codes,
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
        )
