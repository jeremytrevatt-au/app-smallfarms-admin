import asyncio
import os
import sys

sys.path.append(".")

from app.services.platform_api import PlatformApiClient, PlatformApiError  # noqa: E402


async def main() -> None:
    print("Running contract smoke checks...")
    print(f"PLATFORM_API_BASE_URL={os.getenv('PLATFORM_API_BASE_URL', '')}")
    client = PlatformApiClient()

    checks = [
        ("GET moderation submissions", client.list_submissions),
        ("GET audit events", client.list_audit_events),
        ("GET billing subscriptions", client.list_billing_subscriptions),
    ]

    for label, operation in checks:
        try:
            payload = await operation()
            size = len(payload.get("items", payload if isinstance(payload, list) else []))
            print(f"[OK] {label} -> {size} items")
        except PlatformApiError as exc:
            print(f"[FAIL] {label} -> {exc.status_code} {exc.message}")


if __name__ == "__main__":
    asyncio.run(main())
