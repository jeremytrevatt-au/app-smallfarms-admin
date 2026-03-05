from fastapi import APIRouter
from fastapi.responses import RedirectResponse


router = APIRouter()


@router.get("/", include_in_schema=False)
async def home_redirect() -> RedirectResponse:
    return RedirectResponse(url="/moderation", status_code=302)
