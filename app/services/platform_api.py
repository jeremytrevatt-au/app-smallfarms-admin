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
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        started_at = datetime.now(timezone.utc)
        start_perf = time.perf_counter()
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=json_body,
                    params=query_params,
                )
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - start_perf) * 1000)
            self._record_post(
                method=method,
                path=path,
                started_at=started_at,
                latency_ms=latency_ms,
                request_body=json_body,
                request_query=query_params,
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
                nested_error = body.get("error")
                if isinstance(nested_error, dict):
                    message = (
                        nested_error.get("message")
                        or body.get("message")
                        or body.get("detail")
                        or message
                    )
                    error_code = (
                        nested_error.get("code")
                        or body.get("code")
                        or body.get("error_code")
                        or ""
                    )
                else:
                    message = body.get("message") or body.get("detail") or nested_error or message
                    error_code = body.get("code") or body.get("error_code") or ""
                if not isinstance(message, str):
                    message = str(message)
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
                request_query=query_params,
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
                request_query=query_params,
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
            request_query=query_params,
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
        request_query: dict[str, Any] | None,
        status_code: int,
        response_body: Any,
    ) -> None:
        api_log_store.add(
            {
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "method": method.upper(),
                "path": path,
                "request_body": request_body or {},
                "request_query": request_query or {},
                "status_code": status_code,
                "response_body": response_body,
                "latency_ms": latency_ms,
            }
        )

    async def list_submissions(
        self,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        query_params: dict[str, Any] = {}
        if status:
            query_params["status"] = status
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            query_params["page_size"] = page_size
        return await self._request(
            "GET",
            "/v1/admin/moderation/submissions",
            query_params=query_params or None,
        )

    async def claim_submission(self, submission_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/admin/moderation/submissions/{submission_id}/claim"
        )

    async def approve_submission(
        self,
        submission_id: str,
        current_status: str,
        actor_id: str,
        actor_role: str,
        approval_note: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "submission_id": submission_id,
            "current_status": current_status,
            "actor_id": actor_id,
            "actor_role": actor_role,
        }
        if approval_note.strip():
            payload["approval_note"] = approval_note.strip()
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/approve",
            payload,
        )

    async def reject_submission(
        self,
        submission_id: str,
        current_status: str,
        actor_id: str,
        actor_role: str,
        reason_code: str,
        review_notes: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/reject",
            {
                "submission_id": submission_id,
                "current_status": current_status,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "reason_codes": [reason_code],
                "review_notes": review_notes,
            },
        )

    async def request_changes(
        self,
        submission_id: str,
        current_status: str,
        actor_id: str,
        actor_role: str,
        reason_code: str,
        review_notes: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/request-changes",
            {
                "submission_id": submission_id,
                "current_status": current_status,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "reason_codes": [reason_code],
                "review_notes": review_notes,
            },
        )

    async def escalate_submission(
        self,
        submission_id: str,
        current_status: str,
        actor_id: str,
        actor_role: str,
        reason_code: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/escalate",
            {
                "submission_id": submission_id,
                "current_status": current_status,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "reason_code": reason_code,
            },
        )

    async def resolve_escalation(
        self,
        submission_id: str,
        actor_id: str,
        actor_role: str,
        resolution: str,
        review_notes: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "submission_id": submission_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "resolution": resolution,
        }
        if review_notes.strip():
            payload["review_notes"] = review_notes.strip()
        return await self._request(
            "POST",
            f"/v1/admin/moderation/submissions/{submission_id}/resolve-escalation",
            payload,
        )

    async def list_audit_events(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/audit/events")

    async def list_billing_subscriptions(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/billing/subscriptions")

    async def get_public_listing_by_pretty_name(self, pretty_name: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/public/listings/by-pretty-name/{pretty_name}",
        )

    async def create_harvest_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/admin/harvest/jobs",
            payload,
        )

    async def import_places(self, payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        request_payload = dict(payload)
        request_payload["dry_run"] = dry_run
        return await self._request(
            "POST",
            "/v1/admin/places/import",
            request_payload,
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

    async def list_canonical_tags(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/admin/tags")

    async def list_admin_listings(
        self,
        listing_name: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        query_params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if listing_name.strip():
            query_params["listing_name"] = listing_name.strip()
        return await self._request(
            "GET",
            "/v1/admin/listings",
            query_params=query_params,
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

    async def list_listing_tag_assignments(
        self,
        listing_name: str = "",
        tag_name: str = "",
        page: int = 1,
        page_size: int = 25,
        group_by_listing: bool = False,
    ) -> dict[str, Any]:
        query_params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if listing_name.strip():
            query_params["listing_name"] = listing_name.strip()
        if tag_name.strip():
            query_params["tag_name"] = tag_name.strip()
        if group_by_listing:
            query_params["group_by_listing"] = "true"
        return await self._request(
            "GET",
            "/v1/admin/listing-tag-assignments",
            query_params=query_params,
        )

    async def list_listing_tag_matrix(
        self,
        listing_name: str = "",
        tag_name: str = "",
        page: int = 1,
        page_size: int = 25,
        include_inactive_tags: bool = False,
    ) -> dict[str, Any]:
        query_params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if listing_name.strip():
            query_params["listing_name"] = listing_name.strip()
        if tag_name.strip():
            query_params["tag_name"] = tag_name.strip()
        if include_inactive_tags:
            query_params["include_inactive_tags"] = "true"
        return await self._request(
            "GET",
            "/v1/admin/listing-tag-matrix",
            query_params=query_params,
            timeout_seconds=60.0,
        )

    async def apply_listing_tag_matrix_updates(
        self,
        requested_by: str,
        reason_code: str,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/admin/listing-tag-matrix/apply",
            {
                "requested_by": requested_by.strip(),
                "reason_code": reason_code.strip(),
                "updates": updates,
            },
        )

    async def patch_admin_listing(
        self,
        listing_id: str,
        requested_by: str,
        reason_code: str,
        display_name: str = "",
        status_code: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "requested_by": requested_by,
            "reason_code": reason_code,
        }
        if display_name.strip():
            payload["display_name"] = display_name.strip()
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
