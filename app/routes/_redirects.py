from urllib.parse import urlencode
from fastapi.responses import RedirectResponse


def moderation_redirect(message: str, level: str = "success") -> RedirectResponse:
    query = urlencode({"message": message, "level": level})
    return RedirectResponse(url=f"/moderation?{query}", status_code=303)


def harvest_redirect(message: str, level: str = "success") -> RedirectResponse:
    query = urlencode({"message": message, "level": level})
    return RedirectResponse(url=f"/harvest?{query}", status_code=303)
