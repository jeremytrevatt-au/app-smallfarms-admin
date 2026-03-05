from fastapi import APIRouter

from app.deps import platform_client
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/resolve-escalation", include_in_schema=False)
async def resolve_escalation(submission_id: str):
    try:
        await platform_client.resolve_escalation(submission_id)
        return moderation_redirect("Escalation resolved.")
    except PlatformApiError as exc:
        return moderation_redirect(f"Resolve escalation failed: {exc.message}", level="error")
