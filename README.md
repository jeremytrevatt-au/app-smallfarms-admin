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

## Main push update (2026-03-13 10:24 UTC)

1. TODOs completed since last push:
   1. Added admin moderation public-read snapshot support for nullable `pretty_name` and `canonical_path`.
   2. Added admin-facing public pretty-name resolve workflow using `GET /v1/public/listings/by-pretty-name/{pretty_name}`.
   3. Kept admin listing write behavior contract-safe by documenting that `pretty_name` remains premium/member-flow managed.
   4. Added regression coverage for friendly URL fields and `listing_not_found` resolve behavior.
2. Git build references:
   1. `1815702`
3. New understandings/learnings:
   1. Admin applicability for friendly URLs is read-model parity and operator lookup tooling, not admin ownership of `pretty_name` mutation.
   2. A dedicated admin resolve screen reduces contract verification friction while keeping UUID routes and existing moderation workflows unchanged.
4. Understood next steps (remaining TODOs):
   1. Validate moderation and resolve UI against any future public listing payload additions tied to friendly routing.
   2. Keep admin error messaging aligned if platform error-code semantics for pretty-name resolution evolve.

## Main push update (2026-03-15 05:07 UTC)

1. TODOs completed since last push:
   1. Updated `README.md` with the latest main-branch push status entry.
   2. Logged current push context so repository history remains traceable from docs.
2. Git build references:
   1. `a9299bc`
3. New understandings/learnings:
   1. Keeping push-status sections current in `README.md` preserves an auditable narrative aligned with main-branch delivery.
4. Understood next steps (remaining TODOs):
   1. Replace placeholder build reference with the actual commit hash in the next README status refresh.

## Main push update (2026-03-23 01:22 UTC)

1. TODOs completed since last push:
   1. Aligned admin moderation queue loading to the live DB-backed submissions contract with `status`, `page`, and `page_size` query support.
   2. Migrated moderation UI cards to the new item schema (`submission_id`, `listing_id`, `status_code`, `submitted_by_member_id`, `submitted_at`, `submission_payload`).
   3. Added sandboxed iframe rendering for stable `submission_payload.preview_html` and preserved moderation decision actions by `submission_id`.
   4. Updated moderation tests to validate contract mapping, query forwarding, and pagination bound handling.
2. Git build references:
   1. `fc346ab`
3. New understandings/learnings:
   1. Backend now treats `submission_payload.preview_html` as the stable admin preview field and supports direct iframe `srcdoc` rendering with sandbox hardening.
   2. Unknown moderation `status` values return empty result sets rather than errors, so admin filters should preserve operator-entered status strings.
4. Understood next steps (remaining TODOs):
   1. Keep monitoring backend workflow transitions until decision endpoints persist updated `moderation_submission.status_code` values.
   2. Expand moderation status filter UX to enum choices when backend starts persisting additional status values.

## Main push update (2026-03-23 02:08 UTC)

1. TODOs completed since last push:
   1. Fixed moderation approve integration by sending the required backend body model (`submission_id`, `current_status`, `actor_id`, `actor_role`, optional `approval_note`).
   2. Aligned reject/request-changes/escalate/resolve-escalation request bodies to the current backend decision schemas.
   3. Added required manual operator fields (`actor_id`, `actor_role`) and transition fields (`current_status`, `resolution`) in moderation action forms.
   4. Expanded moderation action tests for new required field validation and decision endpoint payload signatures.
2. Git build references:
   1. `68e7fb6`
3. New understandings/learnings:
   1. Moderation decision endpoints now enforce explicit actor and transition metadata, so admin actions must be schema-complete even when legacy UI actions looked body-light.
   2. `requested_by` is not part of moderation decision endpoint schemas and should not be used as a substitute for `actor_id`/`actor_role`.
4. Understood next steps (remaining TODOs):
   1. Validate live end-to-end approval/reject/escalation transitions against backend transition guardrails (`invalid_moderation_transition` paths).
   2. Consider adding shared operator identity persistence in UI state if repeated manual entry becomes operationally expensive.

## Main push update (2026-03-23 03:20 UTC)

1. TODOs completed since last push:
   1. Added moderation action error mapping for backend codes (`moderation_status_conflict`, `submission_not_found`, `validation_failed`, `invalid_moderation_transition`).
   2. Replaced raw backend error payload display with operator-friendly moderation action messages.
   3. Improved platform API error parsing to extract nested backend `error.code` and `error.message` reliably.
   4. Added regression coverage to verify approve conflict mapping shows a refresh-and-retry message.
2. Git build references:
   1. `5f8474e`
3. New understandings/learnings:
   1. Backend error payloads can be nested under `error`, so client-side parsing must handle nested and flat error contracts consistently.
   2. Action-specific error text significantly reduces operator confusion compared to surfacing raw response objects.
4. Understood next steps (remaining TODOs):
   1. Consider adding similar error-code mapping patterns for non-moderation admin domains as backend contracts stabilize.
   2. Evaluate auto-refresh of moderation queue after successful decisions to reduce stale-state retries.

## Main push update (2026-03-23 22:05 UTC)

1. TODOs completed since last push:
   1. Updated moderation queue UX to add one-click filters for pending submissions and auto-approved submissions.
   2. Surfaced `submission_payload.auto_approved_after_initial_moderation` in moderation submission details.
   3. Gated manual moderation controls by status so non-actionable statuses (for example `approved_pending_publish`) show a no-manual-action message.
   4. Added regression coverage for auto-approved status rendering behavior in moderation page tests.
2. Git build references:
   1. `c2c7a0a`
3. New understandings/learnings:
   1. Queue defaults can remain pending-focused while still supporting operational review of auto-approved outcomes through explicit status filters.
   2. Status-aware action gating reduces operator confusion and avoids presenting decision controls where manual moderation is not expected.
4. Understood next steps (remaining TODOs):
   1. Validate escalated-only resolve flow against live payloads to ensure status-driven control visibility remains aligned with backend transition rules.
   2. Consider adding operator-facing explanation text for why controls are hidden on terminal statuses.

## Main push update (2026-03-25 06:09 UTC)

1. TODOs completed since last push:
   1. Updated admin places import transport to use JSON-body `dry_run` instead of `dry_run` query-string parameterization.
   2. Kept harvest jobs POST behavior on JSON body transport, confirming no parameterized request path usage for the existing harvest preview integration.
   3. Validated targeted harvest/import suites after transport alignment to ensure no UI or import preflight regressions.
2. Git build references:
   1. `498f427`
3. New understandings/learnings:
   1. Current admin code path already matched JSON body contracts for harvest job creation; places import was the only parameterized POST transport in active use.
   2. Kill-switch and Stripe webhook endpoints are currently not implemented/consumed in this admin codebase, so no local contract migration was required for those routes.
4. Understood next steps (remaining TODOs):
   1. Add kill-switch admin controls only when backend exposes/requests corresponding admin UX entry points for activate/deactivate operations.
   2. Re-check webhook transport assumptions if Stripe webhook tooling is introduced into this repository.

## Main push update (2026-03-25 07:05 UTC)

1. TODOs completed since last push:
   1. Added listing-tag assignment read integration for `GET /v1/admin/listing-tag-assignments` with pagination and total-count handling.
   2. Added Admin filters for listing name and tag name (case-insensitive contains semantics aligned to backend behavior).
   3. Added grouped projection support (`group_by_listing=true`) with grouped listing/tag rendering while preserving default row-view behavior.
   4. Added regression tests for row rendering, filter forwarding, grouped mode rendering, and 503 availability handling on listing-tag assignment reads.
2. Git build references:
   1. `b3b6a85`
3. New understandings/learnings:
   1. Row-view and grouped-view projections can share the same filter/pagination contract while improving operator readability for listing-centric tag audits.
   2. Name-based filtering in Admin significantly reduces operational friction compared with ID/code-only assignment lookups.
4. Understood next steps (remaining TODOs):
   1. Consider adding direct “open listing management” shortcuts from assignment rows/groups for faster triage workflows.
   2. Monitor grouped projection payload size at higher page sizes and tune default page size if rendering performance drops.

## Main push update (2026-03-25 07:19 UTC)

1. TODOs completed since last push:
   1. Added a full API request/response log panel to the bottom of `/listing-tags` for listing-tag assignment reads/writes.
   2. Extended outbound API logging to include GET requests (not only POST) so read failures like endpoint 404s are visible in Admin UI diagnostics.
   3. Added request query capture in API logs to show exact listing/tag filter parameters sent upstream.
   4. Added regression coverage ensuring listing-tag page renders related API log entries, including Not Found responses.
2. Git build references:
   1. `777023b`
3. New understandings/learnings:
   1. Diagnosing list/read endpoint issues requires method-agnostic logging; POST-only logging leaves critical visibility gaps for read-path failures.
   2. Inline page diagnostics significantly reduce troubleshooting round trips compared with switching to a separate global log page.
4. Understood next steps (remaining TODOs):
   1. Consider adding a clear button/scope toggle for listing-tag diagnostics if log volume grows during active investigations.
   2. Optionally mirror the same inline diagnostics pattern to other admin pages that depend on newly evolving backend contracts.

## Main push update (2026-03-25 07:53 UTC)

1. TODOs completed since last push:
   1. Added a listing-first tag editor on `/listing-tags` where operators click a listing and edit tag assignments via checkboxes.
   2. Loaded canonical tag catalog for editor rendering and preselected currently assigned tags for the selected listing.
   3. Enabled add/remove behavior in a single update by accepting checkbox-based tag selections (including unselect-to-remove and empty selection for clear-all).
   4. Added regression coverage for canonical tag loading, filter forwarding with selector calls, and checkbox-based assignment updates.
2. Git build references:
   1. `e91e2b4`
3. New understandings/learnings:
   1. Listing-first selection with prechecked tags provides a clearer mental model for both adding and removing tags than CSV entry flows.
   2. Read-path selector data and write-path assignment updates can share the same endpoint contract while still supporting operator-friendly editing interactions.
4. Understood next steps (remaining TODOs):
   1. Consider adding listing search pagination controls specific to selector options if assignment inventory grows beyond current first-page selector limit.
   2. Add UI diff preview (`will add`/`will remove`) before submission for higher-confidence bulk taxonomy edits.

## Main push update (2026-03-25 08:14 UTC)

1. TODOs completed since last push:
   1. Updated listing selector data source in `/listing-tags` to use `GET /v1/admin/listings` so listings are selectable even when there are zero assignment rows.
   2. Kept assignment preselection behavior by loading grouped assignment data for the selected listing name and matching by listing ID.
   3. Added API log matching for `GET /v1/admin/listings` so listing-catalog diagnostics appear in the page-level request/response log panel.
   4. Expanded tests for listing catalog integration, selected listing preselection flow, and updated filter forwarding expectations.
2. Git build references:
   1. `11a0c96`
3. New understandings/learnings:
   1. Listing catalog and assignment catalog are distinct concerns; sourcing selectors from assignment rows can hide valid listings when no assignments exist.
   2. Selected-listing precheck remains reliable when combining listing catalog identity with grouped assignment projections for tag state lookup.
4. Understood next steps (remaining TODOs):
   1. Add explicit empty-state helper text when selected listing has no existing assignment rows to confirm that unselected tags represent clear-state rather than load failure.
   2. Add diff preview (`will add`/`will remove`) in the listing editor prior to submission for safer high-impact taxonomy edits.
