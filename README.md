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

