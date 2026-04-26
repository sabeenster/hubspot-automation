# Agentway Lead Automation V1

This is a lightweight internal automation service for Agentway's early-stage lead follow-up workflow.

It keeps HubSpot as the CRM of record while running automation logic outside HubSpot:

- HubSpot provides contacts, demo submissions, and attribution data.
- HubSpot attribution is preserved deeply enough to support future ad-aware personalization.
- Local rule evaluation decides which email should be sent next.
- Gmail is the delivery channel.
- Google Sheets is the visibility layer for operators.
- Granola meeting notes can be linked back to leads after customer calls.
- Tracking endpoints record opens and clicks.
- SQLite provides a small local audit trail during development.

## What this prototype includes

- A Python CLI for syncing contacts, evaluating rules, and generating reports.
- Lead records keep both normalized attribution fields and a raw HubSpot attribution snapshot.
- Rule-based automations for:
  - new lead confirmation
  - demo booking confirmation
  - post-demo follow-up
  - manual status-driven next actions
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
  gmail.py
  granola.py
  hubspot.py
  models.py
  reporting.py
  sheets.py
  templates.py
  tracking_server.py
  webhooks.py
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

## Integration notes

This repo is set up so we can connect real services incrementally:

- `hubspot.py`: fetch contacts or form submissions from HubSpot, including ad and source attribution fields.
- `gmail.py`: send transactional or newsletter emails via Gmail API and store Gmail thread IDs.
- `sheets.py`: mirror state into a Google Sheet for operator visibility.
- `tracking_server.py`: record opens and clicks for outbound emails and accept HubSpot webhooks.
- `granola.py`: poll Granola notes and link them to leads by attendee email.

The service is useful even before every integration is live because the rule engine, data model, reporting, and audit trail are already in place.

## Practical integration decisions

- MailSuite should be treated as a Gmail-native analytics assist, not the only source of truth. This app stores Gmail message IDs, thread IDs, clicks, opens, and replies so analytics are still traceable if MailSuite is used selectively.
- Granola should be synced on a schedule, not via webhook, because Granola's Personal API currently requires polling for new notes.
- HubSpot remains the intake and attribution system, but automation decisions live here.

## Railway deployment

This repo is set up to deploy to Railway as a web service:

- `Procfile` and `railway.toml` start the webhook/tracking server
- Railway should expose the service on `PORT`
- `GET /healthz` returns a simple health response
- `POST /webhooks/hubspot` is the HubSpot webhook target

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
- `GMAIL_ACCESS_TOKEN`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_FROM_NAME`
- `GMAIL_FROM_EMAIL`
- `GOOGLE_SHEET_ID`
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
