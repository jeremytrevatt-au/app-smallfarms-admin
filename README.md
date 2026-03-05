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

