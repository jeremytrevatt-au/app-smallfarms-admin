from fastapi import APIRouter, Form

from app.deps import platform_client
from app.models.forms import parse_transition_form
from app.routes._moderation_error_messages import moderation_action_error
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/approve", include_in_schema=False)
async def approve_submission(
    submission_id: str,
    current_status: str = Form(""),
    actor_id: str = Form(""),
    actor_role: str = Form(""),
    approval_note: str = Form(""),
):
    transition, transition_error = parse_transition_form(
        actor_id=actor_id,
        actor_role=actor_role,
        current_status=current_status,
    )
    if transition_error:
        return moderation_redirect(transition_error, level="error")
    try:
        await platform_client.approve_submission(
            submission_id=submission_id,
            current_status=transition.current_status,
            actor_id=transition.actor_id,
            actor_role=transition.actor_role,
            approval_note=approval_note,
        )
        return moderation_redirect("Submission approved.")
    except PlatformApiError as exc:
        return moderation_redirect(moderation_action_error("Approval", exc), level="error")
