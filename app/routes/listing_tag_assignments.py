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
    assignment_matrix: dict[str, list[str]] | None = None,
    matrix_results: list[dict] | None = None,
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
            "assignment_matrix": assignment_matrix or {},
            "matrix_results": matrix_results or [],
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


def _listing_tag_api_logs(limit: int = 50) -> list[dict]:
    matched: list[dict] = []
    for entry in api_log_store.list_newest_first():
        path = str(entry.get("path", ""))
        if (
            "/v1/admin/listing-tag-assignments" in path
            or "/v1/admin/listing-tag-matrix" in path
            or "/v1/admin/listings" in path
            or "/v1/admin/listings/" in path
            and "/tag-assignments" in path
        ):
            matched.append(entry)
        if len(matched) >= limit:
            break
    return matched


def _normalize_matrix_payload(response: dict) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    raw_tags = response.get("tags", [])
    raw_items = response.get("items", [])
    if not isinstance(raw_tags, list):
        raw_tags = []
    if not isinstance(raw_items, list):
        raw_items = []

    canonical_tags: list[dict] = []
    for entry in raw_tags:
        if not isinstance(entry, dict):
            continue
        tag_code = str(entry.get("tag_code") or entry.get("code") or "").strip()
        if not tag_code:
            continue
        tag_name = str(
            entry.get("tag_name")
            or entry.get("tag_label")
            or entry.get("label")
            or tag_code
        ).strip() or tag_code
        canonical_tags.append(
            {
                "tag_code": tag_code,
                "tag_name": tag_name,
                "is_active": bool(entry.get("is_active", True)),
            }
        )
    canonical_tags.sort(key=lambda item: item["tag_name"].lower())

    listing_options: list[dict] = []
    assignment_matrix: dict[str, list[str]] = {}
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        listing_id = str(entry.get("listing_id") or "").strip()
        if not listing_id:
            continue
        listing_name = str(
            entry.get("display_name") or entry.get("listing_name") or listing_id
        ).strip() or listing_id
        listing_options.append(
            {
                "listing_id": listing_id,
                "listing_name": listing_name,
            }
        )
        assigned_tag_codes_raw = entry.get("assigned_tag_codes", [])
        assigned_tag_codes: list[str] = []
        if isinstance(assigned_tag_codes_raw, list):
            for code in assigned_tag_codes_raw:
                code_text = str(code).strip()
                if code_text:
                    assigned_tag_codes.append(code_text)
        assignment_matrix[listing_id] = sorted(list(set(assigned_tag_codes)))
    return listing_options, canonical_tags, assignment_matrix


def _split_codes_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _filter_tags_for_matrix(canonical_tags: list[dict], tag_name: str) -> list[dict]:
    if not tag_name.strip():
        return [tag for tag in canonical_tags if tag.get("is_active")]
    needle = tag_name.strip().lower()
    return [
        tag
        for tag in canonical_tags
        if tag.get("is_active")
        and (
            needle in str(tag.get("tag_name", "")).lower()
            or needle in str(tag.get("tag_code", "")).lower()
        )
    ]


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
    assignment_matrix: dict[str, list[str]] = {}
    matrix_results: list[dict] = []
    total = 0
    response_page = page
    response_page_size = page_size
    message = ""
    level = "success"
    try:
        response = await platform_client.list_listing_tag_matrix(
            listing_name=listing_name,
            tag_name=tag_name,
            page=page,
            page_size=page_size,
        )
        listing_options, canonical_tags, assignment_matrix = _normalize_matrix_payload(response)
        response_page = _parse_int(str(response.get("page")), page, 1)
        response_page_size = _parse_int(
            str(response.get("page_size")),
            page_size,
            1,
            MAX_PAGE_SIZE,
        )
        total = _parse_int(str(response.get("total")), len(listing_options), 0)
        items = list(listing_options)
    except PlatformApiError as exc:
        message = (
            "database_unavailable: listing tag matrix service unavailable."
            if exc.status_code == 503
            else f"Failed to load listing tag matrix: {exc.message}"
        )
        level = "error"

    if selected_listing_id and listing_options:
        for option in listing_options:
            if option["listing_id"] == selected_listing_id:
                selected_listing_name = option["listing_name"]
                break
        selected_listing_tag_codes = assignment_matrix.get(selected_listing_id, [])

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
        canonical_tags=_filter_tags_for_matrix(canonical_tags, tag_name),
        selected_listing_id=selected_listing_id,
        selected_listing_name=selected_listing_name,
        selected_listing_tag_codes=selected_listing_tag_codes,
        assignment_matrix=assignment_matrix,
        matrix_results=matrix_results,
        api_log_items=_listing_tag_api_logs(),
    )


@router.post("/listing-tags/matrix", include_in_schema=False)
async def apply_listing_tags_matrix(
    request: Request,
    listing_name: str = Form(""),
    tag_name: str = Form(""),
    page: str = Form("1"),
    page_size: str = Form("25"),
    reason_code: str = Form(""),
    requested_by: str = Form(""),
):
    form = await request.form()
    listing_ids = [str(item).strip() for item in form.getlist("listing_ids") if str(item).strip()]
    if not reason_code.strip() or not requested_by.strip():
        return _render_listing_tags(
            request,
            "reason_code and requested_by are required.",
            "error",
            listing_name=listing_name,
            tag_name=tag_name,
            page=_parse_int(page, DEFAULT_PAGE, 1),
            page_size=_parse_int(page_size, DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE),
            reason_code=reason_code,
            requested_by=requested_by,
            api_log_items=_listing_tag_api_logs(),
        )

    updates: list[dict] = []
    for listing_id in listing_ids:
        original_codes = set(_split_codes_csv(str(form.get(f"original_tags__{listing_id}") or "")))
        selected_codes = sorted(
            list(
                {
                    str(code).strip()
                    for code in form.getlist(f"selected_tags__{listing_id}")
                    if str(code).strip()
                }
            )
        )
        selected_set = set(selected_codes)
        if selected_set == original_codes:
            continue
        updates.append(
            {
                "listing_id": listing_id,
                "tag_codes": selected_codes,
            }
        )

    results: list[dict] = []
    changed_count = len(updates)
    message = f"Matrix apply processed {changed_count} changed listing row(s)."
    level = "success"
    if updates:
        try:
            apply_response = await platform_client.apply_listing_tag_matrix_updates(
                requested_by=requested_by.strip(),
                reason_code=reason_code.strip(),
                updates=updates,
            )
            raw_results = apply_response.get("results", [])
            if isinstance(raw_results, list):
                results = [entry for entry in raw_results if isinstance(entry, dict)]
            failure_count = _parse_int(str(apply_response.get("failure_count")), 0, 0)
            success_count = _parse_int(str(apply_response.get("success_count")), 0, 0)
            message = (
                f"Matrix apply completed. Changed rows: {changed_count}. "
                f"Success: {success_count}. Failed: {failure_count}."
            )
            if failure_count > 0:
                level = "error"
        except PlatformApiError as exc:
            message = _assignment_error_message(exc)
            level = "error"

    # Reuse GET loader by calling into same data loading logic.
    listing_name = listing_name.strip()
    tag_name = tag_name.strip()
    selected_listing_id = ""
    page_num = _parse_int(page, DEFAULT_PAGE, 1)
    page_size_num = _parse_int(page_size, DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    group_by_listing = False

    items: list[dict] = []
    grouped_items: list[dict] = []
    listing_options: list[dict] = []
    canonical_tags: list[dict] = []
    assignment_matrix: dict[str, list[str]] = {}
    total = 0
    total_pages = 1
    try:
        response = await platform_client.list_listing_tag_matrix(
            listing_name=listing_name,
            tag_name=tag_name,
            page=page_num,
            page_size=page_size_num,
        )
        listing_options, canonical_tags, assignment_matrix = _normalize_matrix_payload(response)
        items = list(listing_options)
        total = _parse_int(str(response.get("total")), len(listing_options), 0)
        resp_page_size = _parse_int(str(response.get("page_size")), page_size_num, 1, MAX_PAGE_SIZE)
        total_pages = max(1, (total + resp_page_size - 1) // resp_page_size)
    except PlatformApiError as exc:
        message = f"{message} Refresh failed: {exc.message}"
        level = "error"

    return _render_listing_tags(
        request,
        message=message,
        level=level,
        listing_name=listing_name,
        tag_name=tag_name,
        page=page_num,
        page_size=page_size_num,
        total=total,
        total_pages=total_pages,
        group_by_listing=group_by_listing,
        items=items,
        grouped_items=grouped_items,
        listing_options=listing_options,
        canonical_tags=_filter_tags_for_matrix(canonical_tags, tag_name),
        selected_listing_id=selected_listing_id,
        selected_listing_name="",
        selected_listing_tag_codes=[],
        assignment_matrix=assignment_matrix,
        matrix_results=results,
        reason_code=reason_code,
        requested_by=requested_by,
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
