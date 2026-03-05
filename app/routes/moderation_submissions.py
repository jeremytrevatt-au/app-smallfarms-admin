from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.get("/moderation", include_in_schema=False)
async def moderation_queue(request: Request, message: str = "", level: str = "success"):
    submissions: list[dict] = []
    error_message = ""
    try:
        payload = await platform_client.list_submissions()
        submissions = payload.get("items", payload if isinstance(payload, list) else [])
    except PlatformApiError as exc:
        error_message = f"Failed to load moderation queue: {exc.message}"

    return templates.TemplateResponse(
        request=request,
        name="moderation.html",
        context={
            "active_page": "moderation",
            "submissions": submissions,
            "message": message,
            "level": level,
            "error_message": error_message,
        },
    )
