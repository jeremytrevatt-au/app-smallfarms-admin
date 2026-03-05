from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import (
    audit_events,
    billing_subscriptions,
    harvest_jobs,
    home,
    moderation_approve,
    moderation_claim,
    moderation_escalate,
    moderation_reject,
    moderation_request_changes,
    moderation_resolve_escalation,
    moderation_submissions,
)


app = FastAPI(title=settings.app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(home.router)
app.include_router(moderation_submissions.router)
app.include_router(moderation_claim.router)
app.include_router(moderation_approve.router)
app.include_router(moderation_reject.router)
app.include_router(moderation_request_changes.router)
app.include_router(moderation_escalate.router)
app.include_router(moderation_resolve_escalation.router)
app.include_router(audit_events.router)
app.include_router(billing_subscriptions.router)
app.include_router(harvest_jobs.router)
