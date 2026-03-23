from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()

DEFAULT_STATUS = "submitted_pending_review"
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _parse_int(
    value: str | None,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    if parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


@router.get("/moderation", include_in_schema=False)
async def moderation_queue(request: Request, message: str = "", level: str = "success"):
    status = (request.query_params.get("status") or DEFAULT_STATUS).strip() or DEFAULT_STATUS
    page = _parse_int(request.query_params.get("page"), DEFAULT_PAGE, 1)
    page_size = _parse_int(
        request.query_params.get("page_size"),
        DEFAULT_PAGE_SIZE,
        1,
        MAX_PAGE_SIZE,
    )

    submissions: list[dict] = []
    error_message = ""
    response_page = page
    response_page_size = page_size
    total = 0
    try:
        payload = await platform_client.list_submissions(
            status=status,
            page=page,
            page_size=page_size,
        )
        raw_submissions = payload.get("items", [])
        if isinstance(raw_submissions, list):
            for item in raw_submissions:
                if isinstance(item, dict):
                    submissions.append(item)
        response_page = _parse_int(str(payload.get("page")), page, 1)
        response_page_size = _parse_int(str(payload.get("page_size")), page_size, 1, MAX_PAGE_SIZE)
        total = _parse_int(str(payload.get("total")), len(submissions), 0)
    except PlatformApiError as exc:
        error_message = f"Failed to load moderation queue: {exc.message}"

    total_pages = (
        (total + response_page_size - 1) // response_page_size if response_page_size > 0 else 1
    )
    if total_pages < 1:
        total_pages = 1

    return templates.TemplateResponse(
        request=request,
        name="moderation.html",
        context={
            "active_page": "moderation",
            "submissions": submissions,
            "status": status,
            "page": response_page,
            "page_size": response_page_size,
            "total": total,
            "total_pages": total_pages,
            "has_prev_page": response_page > 1,
            "has_next_page": response_page < total_pages,
            "prev_page": response_page - 1 if response_page > 1 else 1,
            "next_page": response_page + 1 if response_page < total_pages else total_pages,
            "message": message,
            "level": level,
            "error_message": error_message,
        },
    )
