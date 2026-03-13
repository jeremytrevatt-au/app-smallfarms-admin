# app-smallfarms-admin

Python web admin app for moderation operations, escalation handling, policy execution support, billing visibility, and places preview workflows through platform-owned contracts.

## Scope implemented

1. Moderation queue workflows:
   1. Claim
   2. Approve
   3. Reject (reason code required)
   4. Request changes (reason code required)
   5. Escalate (reason code required)
   6. Resolve escalation
2. Audit events view.
3. Billing subscriptions support view (read-only, no manual entitlement toggles).
4. Places preview operation using harvest jobs endpoint.

## Tech stack

1. FastAPI + Jinja templates.
2. Material design style UI using Roboto, Material Icons, and custom material-style CSS.
3. Cloud Run container deployment via Dockerfile.

## Local run

1. Create and activate virtual environment:
   1. `python -m venv .venv`
   2. `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (bash)
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment:
   1. `PLATFORM_API_BASE_URL`
   2. `PLATFORM_API_TOKEN`
4. Run server: `uvicorn app.main:app --reload`
5. Open: `http://localhost:8000/moderation`

## Contract smoke checks

1. Run: `python scripts/contract_smoke.py`
2. Uses:
   1. `GET /v1/admin/moderation/submissions`
   2. `GET /v1/admin/audit/events`
   3. `GET /v1/admin/billing/subscriptions`

## Cloud Run deploy

1. Ensure project is active in gcloud.
2. Deploy:
   1. `bash scripts/deploy_cloud_run.sh <gcp-project-id> <service-name> [region]`

## Main push update (2026-03-05 06:35 UTC)

1. TODOs completed since last push:
   1. Enforced import payload contract for `tenant_smallfarms`, including required candidate location and category handling.
   2. Added listing lifecycle management integration for `PATCH /v1/admin/listings/{listing_id}` and `DELETE /v1/admin/listings/{listing_id}` with admin UI and tests.
   3. Added nullable-safe contact rendering in moderation queue cards for admin review (`website_url`, `phone_number`, `social_urls`).
2. Git build references:
   1. `d3d2cbf`
   2. `b480096`
   3. `3e5cf8b`
3. New understandings/learnings:
   1. Contract-correct import now depends on complete location data in selected candidates; missing coordinates are blocked preflight before platform import.
   2. Admin moderation visibility must include contact fields as nullable data to align with cross-team contact contract rollout.
4. Understood next steps (remaining TODOs):
   1. Keep validating live import behavior against platform harvest responses, especially coordinate availability in preview candidates.
   2. Continue admin-only contract alignment updates as platform publishes additional listing profile/contact schema deltas.

## Main push update (2026-03-06 09:17 UTC)

1. TODOs completed since last push:
   1. Aligned admin listing patch flow with tags-first taxonomy rules.
   2. Removed direct `primary_category_code` patching from admin listing management update path.
   3. Restricted listing patch mutable fields to `display_name` and `status_code`, and updated UI guidance to use tag assignments for taxonomy updates.
2. Git build references:
   1. `66eb3f5`
3. New understandings/learnings:
   1. Tags are the canonical taxonomy source, and category/farm-type must be treated as backend-derived compatibility projections.
   2. Admin listing patch endpoint should remain lifecycle-focused (display/status), with taxonomy managed through `POST /v1/admin/listings/{listing_id}/tag-assignments`.
4. Understood next steps (remaining TODOs):
   1. Continue validating admin UX and error messages against future backend taxonomy rule changes.
   2. Keep moderation/operator guidance aligned to tags-first behavior across admin workflows.

## Main push update (2026-03-07 11:01 UTC)

1. TODOs completed since last push:
   1. Reviewed endpoint contract deltas and implemented admin-applicable public read-model alignment only.
   2. Normalized moderation snapshot rendering for explicit `is_premium`/`is_claimed`, contact defaults, tags list shape, and location object with `formatted_address`.
   3. Added moderation UI coverage tests for default-safe rendering, nested listing parity behavior, and partial tag normalization.
2. Git build references:
   1. `4c081fe`
3. New understandings/learnings:
   1. Admin moderation tooling should treat public list/detail shape guarantees as an operator visibility contract, while keeping platform payload as source-of-truth.
   2. Website caching/ETag behavior is not an admin runtime concern; admin applicability is read-model visibility and parity validation.
4. Understood next steps (remaining TODOs):
   1. Continue validating moderation views against future public response guarantee updates from platform.
   2. Keep admin docs synchronized when cross-team contracts add new read-model fields that moderators must review.

## Contract update (friendly URLs and pretty_name)

1. Backend-live summary:
   1. Friendly URL support is live via premium-managed `pretty_name`, public payload additions, and public resolve endpoint support.
   2. Existing UUID-based listing routes remain valid and unchanged.
2. Admin team endpoint contract updates:
   1. Public listing read payloads now include nullable `pretty_name` and `canonical_path` on:
      1. `GET /v1/public/listings`
      2. `GET /v1/public/listings/{listing_id}`
   2. New public resolve endpoint for friendly route lookup:
      1. `GET /v1/public/listings/by-pretty-name/{pretty_name}`
      2. Returns canonical public listing read model including `listing_id`, `pretty_name`, and `canonical_path`.
   3. Unknown `pretty_name` behavior:
      1. HTTP `404`
      2. Error code `listing_not_found`
   4. Admin write endpoint status:
      1. No admin-specific `pretty_name` write route in this release.
      2. Admin should treat `pretty_name` ownership as premium/member-flow managed.
3. Custom-editor team endpoint contract updates:
   1. Member write contract change:
      1. `PATCH /v1/member/listings/{listing_id}/draft` now supports optional `pretty_name` with existing `profile_patch`, `media_refs`, and `client_revision`.
   2. Backend normalization and validation for incoming `pretty_name`:
      1. Lowercase enforced.
      2. Allowed characters: `[a-z0-9-]`.
      3. Leading and trailing hyphens trimmed.
      4. Repeated hyphens collapsed.
      5. Reserved words blocked: `admin`, `api`, `directory`, `farm`, `login`, `signup`, `stories`.
   3. Premium entitlement enforcement:
      1. Non-premium attempts to set `pretty_name` return HTTP `403` with `pretty_name_premium_required`.
   4. Conflict enforcement:
      1. Duplicate normalized value returns HTTP `409` with `pretty_name_conflict`.
   5. Validation error codes expected by client:
      1. `pretty_name_invalid_format`
      2. `pretty_name_reserved_word`
      3. `pretty_name_conflict`
      4. `pretty_name_premium_required`
   6. Response behavior:
      1. Member draft patch response includes normalized saved `pretty_name` for canonical client display.
4. Client integration expectations:
   1. Custom Editor should display and reuse normalized `pretty_name` from patch responses.
   2. Website routing should prefer `/farm/{pretty_name}` when available and continue UUID routes when `pretty_name` is null.
