from fastapi import APIRouter, Form

from app.deps import platform_client
from app.models.forms import parse_reason_form
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/escalate", include_in_schema=False)
async def escalate_submission(
    submission_id: str,
    reason_code: str = Form(""),
    note: str = Form(""),
):
    form, form_error = parse_reason_form(reason_code, note)
    if form_error:
        return moderation_redirect(form_error, level="error")
    try:
        await platform_client.escalate_submission(submission_id, form.reason_code, form.note)
        return moderation_redirect("Submission escalated.")
    except PlatformApiError as exc:
        return moderation_redirect(f"Escalation failed: {exc.message}", level="error")
