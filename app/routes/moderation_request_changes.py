from fastapi import APIRouter, Form

from app.deps import platform_client
from app.models.forms import parse_reason_form, parse_transition_form
from app.routes._moderation_error_messages import moderation_action_error
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/request-changes", include_in_schema=False)
async def request_changes(
    submission_id: str,
    current_status: str = Form(""),
    actor_id: str = Form(""),
    actor_role: str = Form(""),
    reason_code: str = Form(""),
    note: str = Form(""),
):
    transition, transition_error = parse_transition_form(
        actor_id=actor_id,
        actor_role=actor_role,
        current_status=current_status,
    )
    if transition_error:
        return moderation_redirect(transition_error, level="error")
    form, form_error = parse_reason_form(reason_code, note)
    if form_error:
        return moderation_redirect(form_error, level="error")
    if not form.note.strip():
        return moderation_redirect("review_notes is required for this action.", level="error")
    try:
        await platform_client.request_changes(
            submission_id=submission_id,
            current_status=transition.current_status,
            actor_id=transition.actor_id,
            actor_role=transition.actor_role,
            reason_code=form.reason_code,
            review_notes=form.note,
        )
        return moderation_redirect("Changes requested.")
    except PlatformApiError as exc:
        return moderation_redirect(moderation_action_error("Request changes", exc), level="error")
