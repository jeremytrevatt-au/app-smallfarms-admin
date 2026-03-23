from pydantic import BaseModel, Field, ValidationError


class ReasonedActionForm(BaseModel):
    reason_code: str = Field(min_length=1, max_length=128)
    note: str = Field(default="", max_length=2000)


class ModerationActorForm(BaseModel):
    actor_id: str = Field(min_length=1, max_length=256)
    actor_role: str = Field(min_length=1, max_length=128)


class ModerationTransitionForm(ModerationActorForm):
    current_status: str = Field(min_length=1, max_length=128)


class HarvestJobForm(BaseModel):
    query_text: str = Field(min_length=1, max_length=256)
    note: str = Field(default="", max_length=2000)
    search_scope: str = Field(min_length=1, max_length=128)
    region_hint: str = Field(default="", max_length=128)
    category_codes: list[str] = Field(min_length=1)
    max_requests: int = Field(ge=1, le=500)
    max_runtime_minutes: int = Field(ge=1, le=120)
    priority_code: str = Field(min_length=1, max_length=64)
    requested_by: str = Field(min_length=1, max_length=256)


def parse_reason_form(reason_code: str, note: str) -> tuple[ReasonedActionForm | None, str | None]:
    try:
        return ReasonedActionForm(reason_code=reason_code, note=note), None
    except ValidationError:
        return None, "reason_code is required for this action."


def parse_actor_form(actor_id: str, actor_role: str) -> tuple[ModerationActorForm | None, str | None]:
    try:
        return ModerationActorForm(actor_id=actor_id, actor_role=actor_role), None
    except ValidationError:
        return None, "actor_id and actor_role are required for this action."


def parse_transition_form(
    actor_id: str,
    actor_role: str,
    current_status: str,
) -> tuple[ModerationTransitionForm | None, str | None]:
    try:
        return (
            ModerationTransitionForm(
                actor_id=actor_id,
                actor_role=actor_role,
                current_status=current_status,
            ),
            None,
        )
    except ValidationError:
        return None, "current_status, actor_id, and actor_role are required for this action."
