from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _normalized_contact(item: dict) -> dict:
    direct = item.get("contact")
    if isinstance(direct, dict):
        return direct
    profile = item.get("profile")
    if isinstance(profile, dict) and isinstance(profile.get("contact"), dict):
        return profile["contact"]
    profile_patch = item.get("profile_patch")
    if isinstance(profile_patch, dict) and isinstance(profile_patch.get("contact"), dict):
        return profile_patch["contact"]
    return {}


@router.get("/moderation", include_in_schema=False)
async def moderation_queue(request: Request, message: str = "", level: str = "success"):
    submissions: list[dict] = []
    error_message = ""
    try:
        payload = await platform_client.list_submissions()
        raw_submissions = payload.get("items", payload if isinstance(payload, list) else [])
        if isinstance(raw_submissions, list):
            for item in raw_submissions:
                if not isinstance(item, dict):
                    continue
                prepared = dict(item)
                prepared["admin_contact"] = _normalized_contact(item)
                submissions.append(prepared)
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
