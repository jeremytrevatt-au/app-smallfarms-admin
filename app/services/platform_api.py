from __future__ import annotations

from typing import Any
import httpx

from app.config import settings


class PlatformApiError(Exception):
    def __init__(self, status_code: int, message: str, error_code: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class PlatformApiClient:
    def __init__(self) -> None:
        self._base_url = settings.platform_api_base_url.rstrip("/")
        self._token = settings.platform_api_token
        self._timeout = settings.request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self, method: str, path: str, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=json_body,
                )
        except httpx.RequestError as exc:
            raise PlatformApiError(503, f"Platform API unreachable: {exc}") from exc

        if response.status_code >= 400:
            message = response.text
            error_code = ""
            try:
                body = response.json()
                message = body.get("message") or body.get("error") or message
                error_code = body.get("code") or body.get("error_code") or ""
            except ValueError:
                pass
            raise PlatformApiError(response.status_code, message, error_code)

        if not response.content:
            return {}
        return response.json()

    async def list_submissions(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/moderation/submissions")

    async def claim_submission(self, submission_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/admin/moderation/submissions/{submission_id}/claim"
        )

    async def approve_submission(self, submission_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/admin/moderation/submissions/{submission_id}/approve"
        )

    async def reject_submission(
        self, submission_id: str, reason_code: str, note: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/reject",
            {"reason_code": reason_code, "note": note},
        )

    async def request_changes(
        self, submission_id: str, reason_code: str, note: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/request-changes",
            {"reason_code": reason_code, "note": note},
        )

    async def escalate_submission(
        self, submission_id: str, reason_code: str, note: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/escalate",
            {"reason_code": reason_code, "note": note},
        )

    async def resolve_escalation(self, submission_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/admin/moderation/submissions/{submission_id}/resolve-escalation"
        )

    async def list_audit_events(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/audit/events")

    async def list_billing_subscriptions(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/billing/subscriptions")

    async def create_harvest_job(self, source: str, note: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/admin/harvest/jobs",
            {"source": source, "note": note},
        )

    async def import_places(self, payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        flag = "true" if dry_run else "false"
        return await self._request(
            "POST",
            f"/v1/admin/places/import?dry_run={flag}",
            payload,
        )

