from fastapi import APIRouter, Form, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _render_resolve_page(
    request: Request,
    message: str = "",
    level: str = "success",
    pretty_name: str = "",
    result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="public_listing_resolve.html",
        context={
            "active_page": "public-listing-resolve",
            "message": message,
            "level": level,
            "pretty_name": pretty_name,
            "result": result or {},
        },
    )


def _resolve_error_message(exc: PlatformApiError) -> str:
    if exc.status_code == 404 and exc.error_code == "listing_not_found":
        return "listing_not_found: pretty_name does not exist."
    return f"Lookup failed: {exc.message}"


@router.get("/listings/public-resolve", include_in_schema=False)
async def resolve_page(request: Request):
    return _render_resolve_page(request)


@router.post("/listings/public-resolve", include_in_schema=False)
async def resolve_pretty_name(
    request: Request,
    pretty_name: str = Form(""),
):
    if not pretty_name.strip():
        return _render_resolve_page(
            request,
            "pretty_name is required.",
            "error",
            pretty_name=pretty_name,
        )
    try:
        result = await platform_client.get_public_listing_by_pretty_name(
            pretty_name=pretty_name.strip()
        )
        return _render_resolve_page(
            request,
            "Pretty-name lookup succeeded.",
            "success",
            pretty_name=pretty_name,
            result=result,
        )
    except PlatformApiError as exc:
        return _render_resolve_page(
            request,
            _resolve_error_message(exc),
            "error",
            pretty_name=pretty_name,
        )
