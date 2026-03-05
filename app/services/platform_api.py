from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
import time
import httpx

from app.config import settings
from app.services.api_log_store import api_log_store


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
        started_at = datetime.now(timezone.utc)
        start_perf = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=json_body,
                )
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - start_perf) * 1000)
            self._record_post(
                method=method,
                path=path,
                started_at=started_at,
                latency_ms=latency_ms,
                request_body=json_body,
                status_code=503,
                response_body={"error": f"Platform API unreachable: {exc}"},
            )
            raise PlatformApiError(503, f"Platform API unreachable: {exc}") from exc

        if response.status_code >= 400:
            message = response.text
            error_code = ""
            response_body: Any = response.text
            try:
                body = response.json()
                message = body.get("message") or body.get("error") or message
                error_code = body.get("code") or body.get("error_code") or ""
                response_body = body
            except ValueError:
                pass
            latency_ms = int((time.perf_counter() - start_perf) * 1000)
            self._record_post(
                method=method,
                path=path,
                started_at=started_at,
                latency_ms=latency_ms,
                request_body=json_body,
                status_code=response.status_code,
                response_body=response_body,
            )
            raise PlatformApiError(response.status_code, message, error_code)

        latency_ms = int((time.perf_counter() - start_perf) * 1000)
        response_json = {}
        if not response.content:
            self._record_post(
                method=method,
                path=path,
                started_at=started_at,
                latency_ms=latency_ms,
                request_body=json_body,
                status_code=response.status_code,
                response_body=response_json,
            )
            return response_json
        response_json = response.json()
        self._record_post(
            method=method,
            path=path,
            started_at=started_at,
            latency_ms=latency_ms,
            request_body=json_body,
            status_code=response.status_code,
            response_body=response_json,
        )
        return response_json

    def _record_post(
        self,
        method: str,
        path: str,
        started_at: datetime,
        latency_ms: int,
        request_body: dict[str, Any] | None,
        status_code: int,
        response_body: Any,
    ) -> None:
        if method.upper() != "POST":
            return
        api_log_store.add(
            {
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "method": method.upper(),
                "path": path,
                "request_body": request_body or {},
                "status_code": status_code,
                "response_body": response_body,
                "latency_ms": latency_ms,
            }
        )

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

    async def create_harvest_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/admin/harvest/jobs",
            payload,
        )

    async def import_places(self, payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        flag = "true" if dry_run else "false"
        return await self._request(
            "POST",
            f"/v1/admin/places/import?dry_run={flag}",
            payload,
        )

    async def upsert_tags(self, requested_by: str, tags: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/admin/tags",
            {
                "requested_by": requested_by,
                "tags": tags,
            },
        )

    async def replace_listing_tag_assignments(
        self,
        listing_id: str,
        tag_codes: list[str],
        reason_code: str,
        requested_by: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/listings/{listing_id}/tag-assignments",
            {
                "tag_codes": tag_codes,
                "reason_code": reason_code,
                "requested_by": requested_by,
            },
        )

    async def patch_admin_listing(
        self,
        listing_id: str,
        requested_by: str,
        reason_code: str,
        display_name: str = "",
        primary_category_code: str = "",
        status_code: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "requested_by": requested_by,
            "reason_code": reason_code,
        }
        if display_name.strip():
            payload["display_name"] = display_name.strip()
        if primary_category_code.strip():
            payload["primary_category_code"] = primary_category_code.strip()
        if status_code.strip():
            payload["status_code"] = status_code.strip()
        return await self._request(
            "PATCH",
            f"/v1/admin/listings/{listing_id}",
            payload,
        )

    async def delete_admin_listing(
        self,
        listing_id: str,
        requested_by: str,
        reason_code: str,
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/v1/admin/listings/{listing_id}",
            {
                "requested_by": requested_by,
                "reason_code": reason_code,
            },
        )

