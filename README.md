# Agentway Lead Automation

Agentway's internal lead-follow-up service keeps HubSpot as the CRM of record and
turns eligible inbound leads into Gmail drafts for Sabeen to review and send.

## Phase-one workflow

1. HubSpot provides contacts, form submissions, demo activity, and attribution.
2. Agentway classifies each lead and chooses an approved template.
3. A draft request waits for its configured delay.
4. Gmail receives an unsent draft in `sabeen@agentway-ai.com`.
5. Slack announces that the draft is ready and links to Gmail.
6. Sabeen reviews, edits, and manually sends the message.
7. Existing tracking endpoints record opens and clicks after the manual send.
8. Leads, draft events, and meeting notes sync to the operating Google Sheet.

No production code path sends email in phase one. Gmail integration uses
`users.messages.insert` with `labelIds=["DRAFT"]`; Resend and Gmail send endpoints
are disabled.

## Included integrations

- HubSpot lead ingest and webhook handling
- Source, UTM, Meta campaign, ad, and click attribution
- Gmail draft creation with tracking HTML and optional HubSpot BCC
- Slack "draft ready" notifications
- Editable templates and delays in the admin UI
- Google Sheets visibility
- Granola meeting-note linkage
- SQLite state on a Railway persistent volume

## Templates

- `email_signup_confirmation`
- `demo_booking_confirmation`
- `post_demo_followup`

Default draft delays are 10 minutes for email/contact signups, 30 minutes for
demo bookings, and immediate for status-driven post-demo follow-up.

## Quick start

Copy `.env.example` to `.env`, then initialize the database and templates:

```bash
python3 -m src.agentway_leads.cli init-db
python3 -m src.agentway_leads.cli seed-templates
```

Exercise the workflow without touching Gmail:

```bash
python3 -m src.agentway_leads.cli sync-all \
  --hubspot-sample-data sample_contacts.json \
  --granola-sample-data sample_granola_notes.json \
  --skip-sheets \
  --dry-run
```

Run the unit tests:

```bash
python3 -m unittest discover -s tests -v
```

Start the web service:

```bash
python3 -m src.agentway_leads.cli serve-tracking
```

Available endpoints:

- `GET /healthz`
- `GET /admin?admin_token=...`
- `POST /webhooks/hubspot`
- `GET /email/open?event_id=...`
- `GET /r?event_id=...&url=...`

The admin console can edit templates and delays, inspect pending draft
requests, and create a Gmail draft manually. It does not expose a send action.

## Gmail OAuth

Phase one should authorize only:

```text
https://www.googleapis.com/auth/gmail.insert
```

The runtime needs either a short-lived `GMAIL_ACCESS_TOKEN` or refresh-token
credentials. Put credentials directly into Railway; do not commit them.

Required mailbox variables:

```bash
EMAIL_PROVIDER=gmail
EMAIL_FROM_NAME=Sabeen
EMAIL_FROM_EMAIL=sabeen@agentway-ai.com
GMAIL_REFRESH_TOKEN=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REPLY_TO_EMAIL=sabeen@agentway-ai.com
GMAIL_USER_ID=me
HUBSPOT_BCC_EMAIL=
AUTOMATIC_DRAFT_ENABLED=false
AUTOMATIC_EMAIL_ENABLED=false
```

Set `AUTOMATIC_DRAFT_ENABLED=true` only after one manual internal draft has been
verified in Gmail. `AUTOMATIC_EMAIL_ENABLED` is reserved for a later sending
phase and is not used by the phase-one code.

## Railway

The canonical Railway service is `hubspot-automation` in project
`overflowing-flow`.

Recommended commands:

```bash
railway ssh python3 -m src.agentway_leads.cli init-db
railway ssh python3 -m src.agentway_leads.cli seed-templates
railway ssh python3 -m src.agentway_leads.cli sync-hubspot
railway ssh python3 -m src.agentway_leads.cli sync-sheets
```

Use a persistent volume mounted at `/data`:

```bash
DATABASE_PATH=/data/agentway_leads.db
```

The scheduled command should run:

```bash
python3 -m src.agentway_leads.cli sync-all
```

## State model

Draft requests move through:

```text
pending -> drafted
        -> failed
```

Email events keep `draft_created_at` separate from `sent_at`. Creating a draft
sets the lead's `*_drafted` flag but does not set any `*_sent` flag or change
the lead's sales status.

## Google Sheet

The current sheet tabs are:

- `Leads`
- `Email Events`
- `Meeting Notes`

The `Email Events` tab includes `draft_created_at` and `sent_at` separately.

## Portable skill

The repo-backed operating skill is:

`skills/hubspot-lead-automation/SKILL.md`
