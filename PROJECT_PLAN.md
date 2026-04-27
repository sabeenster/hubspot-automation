# Agentway Lead Automation Plan

Last updated: 2026-04-26

## Current objective

Build a lightweight Agentway-owned automation layer that uses:

- HubSpot for lead capture and attribution
- Resend for outbound sending
- Google Sheets for visibility and lightweight ops CRM
- Granola for meeting-note linkage

## Current status

Completed:

- Local Python project scaffold created
- SQLite lead/email/meeting-note store created
- HubSpot sync CLI added
- HubSpot webhook endpoint added
- Resend send path added
- Open/click tracking endpoints added
- Granola note sync and lead linkage added
- HubSpot attribution fields expanded for future ad-aware personalization
- Local git repo initialized and connected to `https://github.com/sabeenster/hubspot-automation.git`
- Railway deployment config added for a hosted webhook/tracking service
- Outbound email moved to a Railway-friendly Resend configuration pattern
- GitHub branch created and pushed: `codex/agentway-lead-automation-v1`
- Railway-ready web service shape documented:
  - web process runs the webhook/tracking server
  - scheduled job runs `sync-all`
- Railway-friendly env naming established for outbound email:
  - `EMAIL_PROVIDER=resend`
  - `EMAIL_FROM_NAME`
  - `EMAIL_FROM_EMAIL`
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
  - `RESEND_REPLY_TO_EMAIL`
- lead-type-specific confirmation timing established:
  - email/newsletter/contact leads: 10 minutes
  - demo bookings: 30 minutes
- lightweight operator UI added at `/admin`:
  - force-send confirmation email for a lead
  - edit per-template delay settings without code changes
  - optional `ADMIN_TOKEN` gate for Railway-hosted access
- testing-safe automatic send gate added:
  - `AUTOMATIC_EMAIL_ENABLED=false` disables automatic sending
  - manual force-send remains available
- template subject/body editing added to the admin UI
- Apps Script-based Google Sheet sync path added so the existing sheet can be updated without requiring a new Google Cloud service-account setup

In progress:

- Tighten live integration behavior and setup docs
- Deploy to Railway and document service/cron setup
- Finish the simpler attached-sheet Apps Script rollout docs and verification

Next:

1. Add provider-agnostic reply detection
2. Improve HubSpot webhook ingestion for real payload variants
3. Deploy to Railway and verify live health/webhook routes
4. Add scheduled Railway job for `sync-all`
5. Verify the Apps Script webhook updates the existing Google Sheet cleanly
6. Decide whether to keep SQLite on a Railway volume or move to Postgres/Supabase later

## Important design decisions

- HubSpot remains the CRM of record and attribution source.
- Automation logic lives outside HubSpot.
- Outbound email uses Resend so Railway-managed secrets match the pattern used by other agents.
- MailSuite is supplemental analytics, not the system of record.
- Granola is polled rather than webhook-driven.
- Lead attribution data should be stored both in normalized fields and raw HubSpot snapshot form.
- Railway hosts the web service and scheduled sync jobs.
- For Google Sheets, default to an Apps Script attached to the existing sheet before introducing a new Google Cloud service-account setup.

## Notes for resumed sessions

- The active project root is this folder.
- The intended GitHub remote is `origin = sabeenster/hubspot-automation`.
- Do not use the unrelated parent repo rooted at `/Users/sabeen`.
- If pushing fails, the user may need to complete GitHub auth in the web UI.
- The active build branch is `codex/agentway-lead-automation-v1`.
- The canonical Google Drive folder for lead-ops assets is:
  - `https://drive.google.com/drive/folders/1OZexKXpIAr4dtT1cX1axHqr7Fa5D6Drc`
- The current sheet used by the workflow is:
  - `https://docs.google.com/spreadsheets/d/1491aWSiFvUIKD43kob7whVljOEDksyOkVXXiBME-g8M/edit?usp=sharing`

## Reusable Pattern For Future Agents

Use this same pattern next time we build a new internal agent unless there is a clear reason to deviate.

### GitHub workflow

1. Create or choose the correct dedicated repo before building.
2. Initialize the local project as its own git repo if the folder lives inside an unrelated parent repo.
3. Add `origin` to the intended GitHub repo.
4. Create a branch with the `codex/` prefix.
5. Commit and push early once the scaffold is usable.
6. Keep `PROJECT_PLAN.md` updated inside the repo so a future session can resume quickly.

### Railway deployment workflow

1. Create a Railway web service from the GitHub repo.
2. Use:
   - `Procfile`
   - `railway.toml`
   - a health endpoint like `GET /healthz`
3. Web service should run the always-on HTTP entrypoint.
4. Scheduled Railway job should run the periodic sync command.
5. Use Railway public domain for both:
   - `BASE_URL`
   - `TRACKING_BASE_URL`
6. Prefer a persistent volume when using SQLite on Railway.

### Google Sheets workflow

1. Prefer updating an already-created Google Sheet instead of creating a new spreadsheet.
2. Default to an Apps Script attached directly to that sheet.
3. Store the deployed Apps Script web app URL in `SHEETS_APPS_SCRIPT_URL`.
4. Use `GOOGLE_SERVICE_ACCOUNT_JSON` only as a fallback when server-to-server Sheets API access is truly needed.

### Email-sending workflow

1. Prefer Resend with Railway-managed env vars over direct Gmail API sending for new agents.
2. Standard env vars:
   - `EMAIL_PROVIDER=resend`
   - `EMAIL_FROM_NAME`
   - `EMAIL_FROM_EMAIL`
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - `RESEND_REPLY_TO_EMAIL`
3. Track outbound events in the app’s own database even if inbox-side tools exist.
4. Keep tracking links and open pixels owned by the app so analytics are portable.
5. Default new agents to a test-safe mode where automatic sending can be disabled independently from manual sends.

### Service shape

For this family of agents, default to:

- Web service:
  receives webhooks, health checks, tracking hits, lightweight admin UI
- Scheduled job:
  runs a single orchestration command such as `sync-all`
- Local DB or hosted DB:
  stores operational state and analytics events

### Handoff expectations

Every future agent repo should include:

- `README.md` with local run steps
- `PROJECT_PLAN.md` with current status and reusable conventions
- `.env.example`
- deployment config for Railway
- one-command scheduled sync entrypoint where practical
- a minimal operator UI when human override/config is part of the workflow
