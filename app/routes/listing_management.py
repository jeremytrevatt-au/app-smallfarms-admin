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


def _normalize_listing_rows(response: dict) -> list[dict]:
    items = response.get("items", [])
    if not isinstance(items, list):
        return []
    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        listing_id = str(item.get("listing_id") or "").strip()
        if not listing_id:
            continue
        listing_name = str(
            item.get("display_name")
            or item.get("listing_name")
            or item.get("name")
            or listing_id
        ).strip() or listing_id
        rows.append(
            {
                "listing_id": listing_id,
                "listing_name": listing_name,
                "status_code": str(item.get("status_code") or item.get("status") or "").strip(),
            }
        )
    return rows


def _render_listing_management(
    request: Request,
    message: str = "",
    level: str = "success",
    listing_name: str = "",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    total: int = 0,
    total_pages: int = 1,
    listing_rows: list[dict] | None = None,
    matrix_results: list[dict] | None = None,
    matrix_requested_by: str = "",
    matrix_reason_code: str = "",
    matrix_delete_enabled: bool = True,
    update_listing_id: str = "",
    update_requested_by: str = "",
    update_reason_code: str = "",
    update_display_name: str = "",
    update_status_code: str = "",
    delete_listing_id: str = "",
    delete_requested_by: str = "",
    delete_reason_code: str = "",
    result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="listing_management.html",
        context={
            "active_page": "listing-management",
            "message": message,
            "level": level,
            "listing_name": listing_name,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "listing_rows": listing_rows or [],
            "matrix_results": matrix_results or [],
            "matrix_requested_by": matrix_requested_by,
            "matrix_reason_code": matrix_reason_code,
            "matrix_delete_enabled": matrix_delete_enabled,
            "has_prev_page": page > 1,
            "has_next_page": page < total_pages,
            "prev_page": page - 1 if page > 1 else 1,
            "next_page": page + 1 if page < total_pages else total_pages,
            "update_listing_id": update_listing_id,
            "update_requested_by": update_requested_by,
            "update_reason_code": update_reason_code,
            "update_display_name": update_display_name,
            "update_status_code": update_status_code,
            "delete_listing_id": delete_listing_id,
            "delete_requested_by": delete_requested_by,
            "delete_reason_code": delete_reason_code,
            "result": result or {},
        },
    )


def _listing_lifecycle_error_message(exc: PlatformApiError, action: str) -> str:
    prefix = "Update listing failed" if action == "patch" else "Delete listing failed"
    if exc.status_code == 404:
        return "listing_not_found: listing_id does not exist."
    if exc.status_code == 422:
        return (
            "validation_failed: check requested_by/reason_code, and patch only display_name/status_code. "
            "Use listing tag assignments for taxonomy updates."
        )
    if exc.status_code == 503:
        return "database_unavailable: listing lifecycle service unavailable."
    return f"{prefix}: {exc.message}"


@router.get("/listings/manage", include_in_schema=False)
async def listing_management_page(request: Request):
    listing_name = (request.query_params.get("listing_name") or "").strip()
    page = _parse_int(request.query_params.get("page"), DEFAULT_PAGE, 1)
    page_size = _parse_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    matrix_delete_enabled = _parse_bool(request.query_params.get("matrix_delete_enabled"), True)

    message = ""
    level = "success"
    listing_rows: list[dict] = []
    total = 0
    response_page = page
    response_page_size = page_size
    try:
        response = await platform_client.list_admin_listings(
            listing_name=listing_name,
            page=page,
            page_size=page_size,
        )
        listing_rows = _normalize_listing_rows(response)
        total = _parse_int(str(response.get("total")), len(listing_rows), 0)
        response_page = _parse_int(str(response.get("page")), page, 1)
        response_page_size = _parse_int(
            str(response.get("page_size")),
            page_size,
            1,
            MAX_PAGE_SIZE,
        )
    except PlatformApiError as exc:
        message = (
            "database_unavailable: listing catalog unavailable."
            if exc.status_code == 503
            else f"Failed to load listings: {exc.message}"
        )
        level = "error"

    total_pages = (
        (total + response_page_size - 1) // response_page_size if response_page_size > 0 else 1
    )
    if total_pages < 1:
        total_pages = 1

    return _render_listing_management(
        request,
        message=message,
        level=level,
        listing_name=listing_name,
        page=response_page,
        page_size=response_page_size,
        total=total,
        total_pages=total_pages,
        listing_rows=listing_rows,
        matrix_delete_enabled=matrix_delete_enabled,
    )


@router.post("/listings/manage/matrix", include_in_schema=False)
async def apply_listing_management_matrix(
    request: Request,
    listing_name: str = Form(""),
    page: str = Form("1"),
    page_size: str = Form("25"),
    matrix_requested_by: str = Form(""),
    matrix_reason_code: str = Form(""),
    matrix_delete_enabled: str = Form("true"),
):
    form = await request.form()
    listing_ids = [str(item).strip() for item in form.getlist("listing_ids") if str(item).strip()]
    delete_enabled = _parse_bool(matrix_delete_enabled, True)
    results: list[dict] = []
    changed_count = 0

    if not matrix_requested_by.strip() or not matrix_reason_code.strip():
        return _render_listing_management(
            request,
            message="requested_by and reason_code are required.",
            level="error",
            listing_name=listing_name,
            page=_parse_int(page, DEFAULT_PAGE, 1),
            page_size=_parse_int(page_size, DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE),
            matrix_requested_by=matrix_requested_by,
            matrix_reason_code=matrix_reason_code,
            matrix_delete_enabled=delete_enabled,
        )

    for listing_id in listing_ids:
        original_display = str(form.get(f"original_display_name__{listing_id}") or "").strip()
        original_status = str(form.get(f"original_status_code__{listing_id}") or "").strip()
        updated_display = str(form.get(f"display_name__{listing_id}") or "").strip()
        updated_status = str(form.get(f"status_code__{listing_id}") or "").strip()
        marked_delete = delete_enabled and _parse_bool(
            str(form.get(f"delete__{listing_id}") or ""),
            False,
        )

        if marked_delete:
            changed_count += 1
            try:
                await platform_client.delete_admin_listing(
                    listing_id=listing_id,
                    requested_by=matrix_requested_by.strip(),
                    reason_code=matrix_reason_code.strip(),
                )
                results.append(
                    {
                        "listing_id": listing_id,
                        "status": "deleted",
                    }
                )
            except PlatformApiError as exc:
                results.append(
                    {
                        "listing_id": listing_id,
                        "status": "failed",
                        "error": _listing_lifecycle_error_message(exc, "delete"),
                    }
                )
            continue

        patch_display = updated_display if updated_display and updated_display != original_display else ""
        patch_status = updated_status if updated_status and updated_status != original_status else ""
        if not patch_display and not patch_status:
            continue
        changed_count += 1
        try:
            await platform_client.patch_admin_listing(
                listing_id=listing_id,
                requested_by=matrix_requested_by.strip(),
                reason_code=matrix_reason_code.strip(),
                display_name=patch_display,
                status_code=patch_status,
            )
            results.append(
                {
                    "listing_id": listing_id,
                    "status": "updated",
                    "display_name": patch_display or original_display,
                    "status_code": patch_status or original_status,
                }
            )
        except PlatformApiError as exc:
            results.append(
                {
                    "listing_id": listing_id,
                    "status": "failed",
                    "error": _listing_lifecycle_error_message(exc, "patch"),
                }
            )

    message = f"Grid apply processed {changed_count} changed listing row(s)."
    level = "success"
    if any(item.get("status") == "failed" for item in results):
        message = f"Grid apply completed with failures. Changed rows: {changed_count}."
        level = "error"

    page_num = _parse_int(page, DEFAULT_PAGE, 1)
    page_size_num = _parse_int(page_size, DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    listing_rows: list[dict] = []
    total = 0
    total_pages = 1
    try:
        response = await platform_client.list_admin_listings(
            listing_name=listing_name.strip(),
            page=page_num,
            page_size=page_size_num,
        )
        listing_rows = _normalize_listing_rows(response)
        total = _parse_int(str(response.get("total")), len(listing_rows), 0)
        response_page_size = _parse_int(
            str(response.get("page_size")),
            page_size_num,
            1,
            MAX_PAGE_SIZE,
        )
        total_pages = max(1, (total + response_page_size - 1) // response_page_size)
    except PlatformApiError as exc:
        message = f"{message} Refresh failed: {exc.message}"
        level = "error"

    return _render_listing_management(
        request,
        message=message,
        level=level,
        listing_name=listing_name.strip(),
        page=page_num,
        page_size=page_size_num,
        total=total,
        total_pages=total_pages,
        listing_rows=listing_rows,
        matrix_results=results,
        matrix_requested_by=matrix_requested_by,
        matrix_reason_code=matrix_reason_code,
        matrix_delete_enabled=delete_enabled,
    )


@router.post("/listings/manage/update", include_in_schema=False)
async def patch_listing(
    request: Request,
    listing_id: str = Form(""),
    requested_by: str = Form(""),
    reason_code: str = Form(""),
    display_name: str = Form(""),
    status_code: str = Form(""),
):
    if not listing_id.strip() or not requested_by.strip() or not reason_code.strip():
        return _render_listing_management(
            request,
            "listing_id, requested_by, and reason_code are required.",
            "error",
            update_listing_id=listing_id,
            update_requested_by=requested_by,
            update_reason_code=reason_code,
            update_display_name=display_name,
            update_status_code=status_code,
        )
    if not display_name.strip() and not status_code.strip():
        return _render_listing_management(
            request,
            "At least one mutable field is required: display_name or status_code.",
            "error",
            update_listing_id=listing_id,
            update_requested_by=requested_by,
            update_reason_code=reason_code,
            update_display_name=display_name,
            update_status_code=status_code,
        )
    try:
        result = await platform_client.patch_admin_listing(
            listing_id=listing_id.strip(),
            requested_by=requested_by.strip(),
            reason_code=reason_code.strip(),
            display_name=display_name,
            status_code=status_code,
        )
        return _render_listing_management(
            request,
            "Listing updated.",
            "success",
            update_listing_id=listing_id,
            update_requested_by=requested_by,
            update_reason_code=reason_code,
            update_display_name=display_name,
            update_status_code=status_code,
            result=result,
        )
    except PlatformApiError as exc:
        return _render_listing_management(
            request,
            _listing_lifecycle_error_message(exc, "patch"),
            "error",
            update_listing_id=listing_id,
            update_requested_by=requested_by,
            update_reason_code=reason_code,
            update_display_name=display_name,
            update_status_code=status_code,
        )


@router.post("/listings/manage/delete", include_in_schema=False)
async def delete_listing(
    request: Request,
    listing_id: str = Form(""),
    requested_by: str = Form(""),
    reason_code: str = Form(""),
):
    if not listing_id.strip() or not requested_by.strip() or not reason_code.strip():
        return _render_listing_management(
            request,
            "listing_id, requested_by, and reason_code are required for delete.",
            "error",
            delete_listing_id=listing_id,
            delete_requested_by=requested_by,
            delete_reason_code=reason_code,
        )
    try:
        result = await platform_client.delete_admin_listing(
            listing_id=listing_id.strip(),
            requested_by=requested_by.strip(),
            reason_code=reason_code.strip(),
        )
        return _render_listing_management(
            request,
            "Listing deleted (soft-delete).",
            "success",
            delete_listing_id=listing_id,
            delete_requested_by=requested_by,
            delete_reason_code=reason_code,
            result=result,
        )
    except PlatformApiError as exc:
        return _render_listing_management(
            request,
            _listing_lifecycle_error_message(exc, "delete"),
            "error",
            delete_listing_id=listing_id,
            delete_requested_by=requested_by,
            delete_reason_code=reason_code,
        )
