from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _render_listing_management(
    request: Request,
    message: str = "",
    level: str = "success",
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
    return _render_listing_management(request)


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
