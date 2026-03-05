from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _render_listing_tags(
    request: Request,
    message: str = "",
    level: str = "success",
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
        return "database_unavailable: tag assignment service unavailable."
    return f"Tag assignment failed: {exc.message}"


@router.get("/listing-tags", include_in_schema=False)
async def listing_tags_page(request: Request):
    return _render_listing_tags(request)


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
