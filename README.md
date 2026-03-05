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

