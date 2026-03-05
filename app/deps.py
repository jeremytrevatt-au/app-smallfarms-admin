from fastapi.templating import Jinja2Templates

from app.services.platform_api import PlatformApiClient


templates = Jinja2Templates(directory="templates")
platform_client = PlatformApiClient()
