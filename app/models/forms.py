from pydantic import BaseModel, Field, ValidationError


class ReasonedActionForm(BaseModel):
    reason_code: str = Field(min_length=1, max_length=128)
    note: str = Field(default="", max_length=2000)


class HarvestJobForm(BaseModel):
    source: str = Field(min_length=1, max_length=128)
    note: str = Field(default="", max_length=2000)
    search_scope: str = Field(min_length=1, max_length=128)
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
