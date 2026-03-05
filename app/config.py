from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "SmallFarms Admin"
    platform_api_base_url: str = os.getenv("PLATFORM_API_BASE_URL", "http://localhost:8081")
    platform_api_token: str = os.getenv("PLATFORM_API_TOKEN", "")
    request_timeout_seconds: float = float(os.getenv("PLATFORM_API_TIMEOUT_SECONDS", "20"))


settings = Settings()
