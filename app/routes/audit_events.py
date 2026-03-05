from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.get("/audit", include_in_schema=False)
async def audit_events(request: Request):
    events: list[dict] = []
    error_message = ""
    try:
        payload = await platform_client.list_audit_events()
        events = payload.get("items", payload if isinstance(payload, list) else [])
    except PlatformApiError as exc:
        error_message = f"Failed to load audit events: {exc.message}"

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "active_page": "audit",
            "events": events,
            "error_message": error_message,
        },
    )
