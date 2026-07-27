---
name: hubspot-lead-automation
description: Run and maintain the Agentway HubSpot lead automation workflow on Railway, including HubSpot lead ingest, Gmail draft creation, Slack draft-ready notifications, Google Sheet sync, tracking, and Granola linkage.
---

# HubSpot Lead Automation

Use this skill for the Agentway lead automation service:

- Repo: `https://github.com/sabeenster/hubspot-automation`
- Local checkout: `/Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and`
- Railway project: `overflowing-flow`
- Railway service: `hubspot-automation`
- Branch: `codex/agentway-lead-automation-v1`

## Phase-one invariant

HubSpot leads may create Gmail drafts. The application must not send email.

The Gmail client must call:

```text
POST /gmail/v1/users/{userId}/messages
labelIds=["DRAFT"]
```

It must not call `messages/send` or `drafts/send`. Prefer a Gmail OAuth token
authorized only for `https://www.googleapis.com/auth/gmail.insert`.

## Workflow

1. New form submissions and demo activity land in HubSpot.
2. Webhook or scheduled sync creates or updates the local lead.
3. Rule evaluation queues a draft request.
4. When the template delay has elapsed and automatic drafting is enabled,
   Gmail receives a draft for `sabeen@agentway-ai.com`.
5. Slack posts "draft ready" with links to Gmail and the admin UI.
6. Sabeen reviews and manually sends.
7. Open and click tracking remain available through the Railway service.

## Core environment

```bash
APP_ENV=production
BASE_URL=https://hubspot-automation-production.up.railway.app
TRACKING_BASE_URL=https://hubspot-automation-production.up.railway.app
DATABASE_PATH=/data/agentway_leads.db
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
SLACK_WEBHOOK_URL=
ADMIN_TOKEN=
SHEETS_APPS_SCRIPT_URL=
```

Keep `AUTOMATIC_DRAFT_ENABLED=false` until one internal draft has been
verified. `AUTOMATIC_EMAIL_ENABLED` is reserved and unused in phase one.

## Railway commands

```bash
cd /Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and
railway ssh python3 -m src.agentway_leads.cli init-db
railway ssh python3 -m src.agentway_leads.cli seed-templates
railway ssh python3 -m src.agentway_leads.cli sync-hubspot
railway ssh python3 -m src.agentway_leads.cli sync-sheets
```

The scheduled command is:

```bash
python3 -m src.agentway_leads.cli sync-all
```

## Expected templates

- `email_signup_confirmation`
- `demo_booking_confirmation`
- `post_demo_followup`

Templates and delays are editable in `/admin`.

## Verification

Before enabling automatic drafts:

1. Run `python3 -m unittest discover -s tests -v`.
2. Confirm no production URL contains `/send`.
3. Run `sync-all --dry-run` with sample inputs.
4. Initialize and migrate the Railway database.
5. Create one draft manually from the admin UI.
6. Confirm the draft appears in `sabeen@agentway-ai.com` with the correct To,
   From, Reply-To, subject, body, tracking links, and optional HubSpot BCC.
7. Confirm no `sent_at` or `*_sent` field was changed.
8. Only then enable `AUTOMATIC_DRAFT_ENABLED=true`.

## Common failures

- Gmail draft credentials missing:
  - the app raises an error and must not record a fake draft
- Gmail returns 403:
  - refresh the OAuth token and confirm `gmail.insert` was authorized
- Draft does not appear:
  - confirm the Gmail response returned a message ID and included the `DRAFT`
    label
- Duplicate drafts:
  - check the unique lead/template draft request and `*_drafted` fields
- Slack notification missing:
  - confirm `SLACK_WEBHOOK_URL`; Slack is notified after Gmail draft creation
- Data clears on deploy:
  - confirm the Railway volume is mounted at `/data`

## Data state

- Lead draft state uses `last_email_drafted` and template-specific
  `*_drafted` flags.
- Actual send state remains separate in `last_email_sent`, `sent_at`, and
  `*_sent` fields for the future sending phase.
- Google Sheet tabs remain `Leads`, `Email Events`, and `Meeting Notes`.
