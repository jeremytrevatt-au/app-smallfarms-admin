from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


@router.get("/billing", include_in_schema=False)
async def billing_subscriptions(request: Request):
    subscriptions: list[dict] = []
    error_message = ""
    try:
        payload = await platform_client.list_billing_subscriptions()
        subscriptions = payload.get("items", payload if isinstance(payload, list) else [])
    except PlatformApiError as exc:
        error_message = f"Failed to load subscriptions: {exc.message}"

    return templates.TemplateResponse(
        request=request,
        name="billing.html",
        context={
            "active_page": "billing",
            "subscriptions": subscriptions,
            "error_message": error_message,
        },
    )
