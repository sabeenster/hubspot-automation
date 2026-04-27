# Agentway Lead Automation V1

This is a lightweight internal automation service for Agentway's early-stage lead follow-up workflow.

It keeps HubSpot as the CRM of record while running automation logic outside HubSpot:

- HubSpot provides contacts, demo submissions, and attribution data.
- HubSpot attribution is preserved deeply enough to support future ad-aware personalization.
- Local rule evaluation decides which email should be sent next.
- Resend is the delivery channel.
- Google Sheets is the visibility layer for operators, using an Apps Script attached to the existing sheet by default.
- Granola meeting notes can be linked back to leads after customer calls.
- Tracking endpoints record opens and clicks.
- SQLite provides a small local audit trail during development.

## What this prototype includes

- A Python CLI for syncing contacts, evaluating rules, and generating reports.
- Lead records keep both normalized attribution fields and a raw HubSpot attribution snapshot.
- Rule-based automations for:
  - email signup confirmation
  - demo booking confirmation
  - post-demo follow-up
  - manual status-driven next actions
- Confirmation timing defaults:
  - newsletter/contact/email leads: 10 minutes
  - demo bookings: 30 minutes
- A tiny tracking server for open pixels and click redirects.
- A webhook endpoint for HubSpot contact events.
- A Granola sync flow for linking meeting notes to known leads by attendee email.
- A seed template file you can edit without touching code.
- A local SQLite database for leads, email events, and activity logs.

## What is intentionally not overbuilt yet

- No visual campaign builder
- No advanced lead scoring
- No A/B testing
- No full CRM replacement
- No dependency on paid HubSpot workflow tiers

## Structure

```text
src/agentway_leads/
  automation.py
  cli.py
  config.py
  database.py
  email_sender.py
  granola.py
  hubspot.py
  models.py
  reporting.py
  sheets.py
  templates.py
  tracking_server.py
  webhooks.py
apps_script/
  lead_sheet_sync.gs
templates/
  seed_templates.json
.env.example
```

## Quick start

1. Copy `.env.example` to `.env` and fill in credentials later.
2. Run a one-time local bootstrap:

```bash
python3 -m src.agentway_leads.cli init-db
python3 -m src.agentway_leads.cli seed-templates
```

3. Import a sample HubSpot payload:

```bash
python3 -m src.agentway_leads.cli sync-hubspot --sample-data sample_contacts.json
```

4. Evaluate automations:

```bash
python3 -m src.agentway_leads.cli run-automations --dry-run
```

5. Start tracking endpoints locally:

```bash
python3 -m src.agentway_leads.cli serve-tracking
```

This server also exposes a HubSpot webhook endpoint at `/webhooks/hubspot`.

6. Link Granola meeting notes:

```bash
python3 -m src.agentway_leads.cli sync-granola --sample-data sample_granola_notes.json
```

7. Generate a weekly report:

```bash
python3 -m src.agentway_leads.cli weekly-report
```

8. Run the full cycle in one command:

```bash
python3 -m src.agentway_leads.cli sync-all --dry-run
```

The default timing behavior is:

- email/newsletter/contact leads receive confirmation after 10 minutes
- demo bookings receive confirmation after 30 minutes
- post-demo follow-up remains status-driven

## Integration notes

This repo is set up so we can connect real services incrementally:

- `hubspot.py`: fetch contacts or form submissions from HubSpot, including ad and source attribution fields.
- `email_sender.py`: send transactional or newsletter emails via Resend using Railway-friendly env vars.
- `sheets.py`: mirror state into a Google Sheet for operator visibility, preferably through an Apps Script webhook attached to the target sheet.
- `tracking_server.py`: record opens and clicks for outbound emails and accept HubSpot webhooks.
- `granola.py`: poll Granola notes and link them to leads by attendee email.

The service is useful even before every integration is live because the rule engine, data model, reporting, and audit trail are already in place.

## Practical integration decisions

- MailSuite can still be used as a useful inbox-side assist, but outbound delivery now runs through Resend so Railway-managed API credentials match the rest of your agents.
- Granola should be synced on a schedule, not via webhook, because Granola's Personal API currently requires polling for new notes.
- HubSpot remains the intake and attribution system, but automation decisions live here.

## Railway deployment

This repo is set up to deploy to Railway as a web service:

- `Procfile` and `railway.toml` start the webhook/tracking server
- Railway should expose the service on `PORT`
- `GET /healthz` returns a simple health response
- `POST /webhooks/hubspot` is the HubSpot webhook target
- `GET /admin` provides an operator UI for manual confirmation sends and delay configuration

Recommended Railway shape:

1. Web service:
   runs `python3 -m src.agentway_leads.cli serve-tracking`
2. Scheduled command:
   runs `python3 -m src.agentway_leads.cli sync-all`

Recommended Railway environment variables:

- `APP_ENV=production`
- `BASE_URL=https://your-railway-domain`
- `TRACKING_BASE_URL=https://your-railway-domain`
- `HOST=0.0.0.0`
- `PORT=${{PORT}}`
- `DATABASE_PATH=/data/agentway_leads.db` if using a mounted volume
- `HUBSPOT_ACCESS_TOKEN`
- `HUBSPOT_WEBHOOK_SECRET`
- `EMAIL_PROVIDER=resend`
- `EMAIL_FROM_NAME`
- `EMAIL_FROM_EMAIL`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `RESEND_REPLY_TO_EMAIL`
- `ADMIN_TOKEN`
- `AUTOMATIC_EMAIL_ENABLED=false` during testing
- `GOOGLE_SHEET_ID`
- `SHEETS_APPS_SCRIPT_URL`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GRANOLA_API_KEY`
- `GRANOLA_API_BASE`

Recommended Railway setup steps:

1. Create a new Railway project from this GitHub repo
2. Select branch `codex/agentway-lead-automation-v1` or merge it to your main branch first
3. Add the environment variables above
4. Add a persistent volume and point `DATABASE_PATH` at it if you want SQLite persistence across deploys
5. Deploy the web service
6. Confirm `GET /healthz` works
7. Point HubSpot webhooks to `https://your-domain/webhooks/hubspot`
8. Add a Railway scheduled job for `python3 -m src.agentway_leads.cli sync-all`

## Simpler Google Sheet setup

If you already have the sheet you want to use, the simplest setup is:

1. Use this Google Drive folder as the canonical home for the lead-ops assets:
   - [Agentway lead ops folder](https://drive.google.com/drive/folders/1OZexKXpIAr4dtT1cX1axHqr7Fa5D6Drc)
2. Open the existing spreadsheet:
   - [Agentway lead sheet](https://docs.google.com/spreadsheets/d/1491aWSiFvUIKD43kob7whVljOEDksyOkVXXiBME-g8M/edit?usp=sharing)
3. Open `Extensions -> Apps Script`
4. Paste in [apps_script/lead_sheet_sync.gs](/Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and/apps_script/lead_sheet_sync.gs)
5. Deploy it as a web app:
   - execute as: `Me`
   - who has access: `Anyone with the link`
6. Copy the deployed web app URL into:
   - `SHEETS_APPS_SCRIPT_URL`
7. Set:
   - `GOOGLE_SHEET_ID=1491aWSiFvUIKD43kob7whVljOEDksyOkVXXiBME-g8M`

That attached-sheet Apps Script path is now the preferred setup for this project.

The older `GOOGLE_SERVICE_ACCOUNT_JSON` route still works as a fallback, but it is no longer the recommended first step.

## Operator UI

The app also exposes a lightweight admin console:

- `/admin` shows recent leads and template delays
- you can force-send a chosen template for a lead
- you can update per-template delays such as 10 minutes or 30 minutes
- you can edit template subject/body content directly in the UI
- it shows whether automatic sending is currently enabled

If `ADMIN_TOKEN` is set, open:

- `/admin?admin_token=YOUR_TOKEN`

That keeps the UI usable on a public Railway service without leaving it completely open.

## Testing mode

To keep the app from automatically sending while you test:

- set `AUTOMATIC_EMAIL_ENABLED=false`

In that mode:

- leads still sync in from HubSpot
- the admin UI still works
- manual force-send from `/admin` still works
- scheduled and automatic sends do not go out

## Attribution data

The lead model now keeps:

- normalized source fields such as `source`, `source_drilldown_1`, `source_drilldown_2`
- UTM fields such as `utm_campaign`, `utm_ad`, and `utm_content`
- ad-aware fields such as `ad_campaign_name`, `ad_campaign_id`, `ad_id`, and `ad_network`
- a raw `attribution_snapshot_json` copy of key HubSpot attribution properties

That gives us enough structure to segment later on things like:

- Meta leads vs direct demo traffic
- campaign-specific follow-up
- creative-aware personalization
- “people who came from ops pain point ads” vs “people who came from founder story ads”
