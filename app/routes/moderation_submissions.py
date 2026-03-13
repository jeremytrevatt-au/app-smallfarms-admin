from fastapi import APIRouter, Request

from app.deps import platform_client, templates
from app.services.platform_api import PlatformApiError


router = APIRouter()


def _source_listing(item: dict) -> dict:
    for key in ("listing", "public_listing", "listing_snapshot"):
        candidate = item.get(key)
        if isinstance(candidate, dict):
            return candidate
    return item


def _normalized_contact(item: dict) -> dict:
    direct = item.get("contact")
    if isinstance(direct, dict):
        return direct
    profile = item.get("profile")
    if isinstance(profile, dict) and isinstance(profile.get("contact"), dict):
        return profile["contact"]
    profile_patch = item.get("profile_patch")
    if isinstance(profile_patch, dict) and isinstance(profile_patch.get("contact"), dict):
        return profile_patch["contact"]
    return {}


def _normalized_public_read_model(item: dict) -> dict:
    source = _source_listing(item)
    tags_raw = source.get("tags")
    tags: list[dict] = []
    if isinstance(tags_raw, list):
        for entry in tags_raw:
            if not isinstance(entry, dict):
                continue
            tags.append(
                {
                    "code": str(entry.get("code") or ""),
                    "label": str(entry.get("label") or ""),
                }
            )
    contact = _normalized_contact(source)
    social_urls = contact.get("social_urls")
    if not isinstance(social_urls, dict):
        social_urls = {}
    location = source.get("location")
    if not isinstance(location, dict):
        location = {}
    normalized_location = {
        "lat": location.get("lat"),
        "lng": location.get("lng"),
        "formatted_address": str(location.get("formatted_address") or ""),
        "precision_flag": str(location.get("precision_flag") or ""),
        "viewport_hint": location.get("viewport_hint")
        if isinstance(location.get("viewport_hint"), dict)
        else {},
    }
    normalized_contact = {
        "website_url": str(contact.get("website_url") or ""),
        "phone_number": str(contact.get("phone_number") or ""),
        "social_urls": social_urls,
    }
    return {
        "display_name": str(source.get("display_name") or ""),
        "pretty_name": str(source.get("pretty_name") or ""),
        "canonical_path": str(source.get("canonical_path") or ""),
        "is_premium": bool(source.get("is_premium", False)),
        "is_claimed": bool(source.get("is_claimed", False)),
        "primary_category_code": str(source.get("primary_category_code") or ""),
        "farm_type_code": str(source.get("farm_type_code") or ""),
        "summary": str(source.get("summary") or ""),
        "location": normalized_location,
        "contact": normalized_contact,
        "tags": tags,
    }


@router.get("/moderation", include_in_schema=False)
async def moderation_queue(request: Request, message: str = "", level: str = "success"):
    submissions: list[dict] = []
    error_message = ""
    try:
        payload = await platform_client.list_submissions()
        raw_submissions = payload.get("items", payload if isinstance(payload, list) else [])
        if isinstance(raw_submissions, list):
            for item in raw_submissions:
                if not isinstance(item, dict):
                    continue
                prepared = dict(item)
                prepared["admin_public_read_model"] = _normalized_public_read_model(item)
                submissions.append(prepared)
    except PlatformApiError as exc:
        error_message = f"Failed to load moderation queue: {exc.message}"

    return templates.TemplateResponse(
        request=request,
        name="moderation.html",
        context={
            "active_page": "moderation",
            "submissions": submissions,
            "message": message,
            "level": level,
            "error_message": error_message,
        },
    )
