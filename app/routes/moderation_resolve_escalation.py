from fastapi import APIRouter, Form

from app.deps import platform_client
from app.models.forms import parse_actor_form
from app.routes._redirects import moderation_redirect
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.post("/moderation/{submission_id}/resolve-escalation", include_in_schema=False)
async def resolve_escalation(
    submission_id: str,
    actor_id: str = Form(""),
    actor_role: str = Form(""),
    resolution: str = Form(""),
    review_notes: str = Form(""),
):
    actor, actor_error = parse_actor_form(actor_id=actor_id, actor_role=actor_role)
    if actor_error:
        return moderation_redirect(actor_error, level="error")
    allowed_resolutions = {"approve", "reject", "request_changes"}
    if resolution not in allowed_resolutions:
        return moderation_redirect(
            "resolution must be one of: approve, reject, request_changes.",
            level="error",
        )
    try:
        await platform_client.resolve_escalation(
            submission_id=submission_id,
            actor_id=actor.actor_id,
            actor_role=actor.actor_role,
            resolution=resolution,
            review_notes=review_notes,
        )
        return moderation_redirect("Escalation resolved.")
    except PlatformApiError as exc:
        return moderation_redirect(f"Resolve escalation failed: {exc.message}", level="error")
