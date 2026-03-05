from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.models.forms import HarvestJobForm
from app.routes._redirects import harvest_redirect
from app.services.platform_api import PlatformApiError
from pydantic import ValidationError


router = APIRouter()


@router.get("/harvest", include_in_schema=False)
async def harvest_page(request: Request, message: str = "", level: str = "success"):
    return templates.TemplateResponse(
        request=request,
        name="harvest.html",
        context={
            "active_page": "harvest",
            "message": message,
            "level": level,
        },
    )


@router.post("/harvest/jobs", include_in_schema=False)
async def create_harvest_job(source: str = Form(""), note: str = Form("")):
    try:
        form = HarvestJobForm(source=source, note=note)
    except ValidationError:
        return harvest_redirect("source is required.", level="error")

    try:
        await platform_client.create_harvest_job(form.source, form.note)
        return harvest_redirect("Harvest job started.")
    except PlatformApiError as exc:
        return harvest_redirect(f"Harvest job failed: {exc.message}", level="error")
