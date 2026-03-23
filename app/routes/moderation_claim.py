from fastapi import APIRouter

from app.deps import platform_client
from app.routes._moderation_error_messages import moderation_action_error
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/claim", include_in_schema=False)
async def claim_submission(submission_id: str):
    try:
        await platform_client.claim_submission(submission_id)
        return moderation_redirect("Submission claimed.")
    except PlatformApiError as exc:
        return moderation_redirect(moderation_action_error("Claim", exc), level="error")
