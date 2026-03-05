from fastapi import APIRouter, Request

from app.deps import templates
from app.services.api_log_store import api_log_store


router = APIRouter()


@router.get("/api-logs", include_in_schema=False)
async def api_logs_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="api_logs.html",
        context={
            "active_page": "api-logs",
            "items": api_log_store.list_newest_first(),
        },
    )
