from app.services.platform_api import PlatformApiError


ERROR_CODE_MESSAGES: dict[str, str] = {
    "moderation_status_conflict": "Submission status changed. Refresh the queue and retry.",
    "submission_not_found": "Submission not found.",
    "validation_failed": "Request validation failed. Check required fields and retry.",
    "invalid_moderation_transition": "Decision is not allowed from the current submission status.",
}


def moderation_action_error(action_label: str, exc: PlatformApiError) -> str:
    mapped = ERROR_CODE_MESSAGES.get(exc.error_code)
    if mapped:
        return f"{action_label} failed: {mapped}"
    if exc.message:
        return f"{action_label} failed: {exc.message}"
    return f"{action_label} failed."
