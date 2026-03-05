from fastapi import APIRouter

from app.deps import platform_client
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/approve", include_in_schema=False)
async def approve_submission(submission_id: str):
    try:
        await platform_client.approve_submission(submission_id)
        return moderation_redirect("Submission approved.")
    except PlatformApiError as exc:
        return moderation_redirect(f"Approval failed: {exc.message}", level="error")
