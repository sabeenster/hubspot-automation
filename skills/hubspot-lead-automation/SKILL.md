---
name: hubspot-lead-automation
description: Run and maintain the Agentway HubSpot lead automation workflow on Railway. Use when Codex needs to sync HubSpot leads, seed templates, push lead data into the shared Google Sheet via Apps Script, diagnose Railway/HubSpot/Sheets issues, or operate the live admin UI and persistent datastore.
---

# HubSpot Lead Automation

Use this skill for the Agentway lead automation service in:

- Repo: `https://github.com/sabeenster/hubspot-automation`
- Typical local checkout: `/Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and`
- Railway project: `overflowing-flow`
- Railway service: `hubspot-automation`
- Branch: `codex/agentway-lead-automation-v1`

## What this workflow owns

- HubSpot lead ingest and attribution
- Railway-hosted admin UI and webhook service
- Slack approval notifications for new submissions and demo bookings
- Gmail sending after explicit approval
- Google Sheet sync through Apps Script
- Granola meeting-note linkage
- SQLite state, ideally on a Railway volume

## Key URLs

- Railway admin UI:
  - `https://hubspot-automation-production.up.railway.app/admin?admin_token=43046721`
- Railway health:
  - `https://hubspot-automation-production.up.railway.app/healthz`
- Google Sheet:
  - `https://docs.google.com/spreadsheets/d/1491aWSiFvUIKD43kob7whVljOEDksyOkVXXiBME-g8M/edit?usp=sharing`
- Google Drive folder:
  - `https://drive.google.com/drive/folders/1OZexKXpIAr4dtT1cX1axHqr7Fa5D6Drc`

## Railway-first workflow

Prefer Railway over localhost for real testing.

1. Make sure the repo is on the current branch and pushed.
2. Confirm Railway has the latest deployment.
3. Confirm core vars:
   - `APP_ENV=production`
   - `BASE_URL=https://hubspot-automation-production.up.railway.app`
   - `TRACKING_BASE_URL=https://hubspot-automation-production.up.railway.app`
   - `DATABASE_PATH=/data/agentway_leads.db`
   - `AUTOMATIC_EMAIL_ENABLED=false` during testing
   - `EMAIL_PROVIDER=gmail`
   - `GMAIL_ACCESS_TOKEN` or refresh-token-based Gmail OAuth vars
   - `SLACK_WEBHOOK_URL`
   - `SHEETS_APPS_SCRIPT_URL=<current /exec URL>`
4. Use Railway remote commands from macOS terminal:

```bash
cd /Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and
railway ssh python3 -m src.agentway_leads.cli init-db
railway ssh python3 -m src.agentway_leads.cli seed-templates
railway ssh python3 -m src.agentway_leads.cli sync-hubspot
railway ssh python3 -m src.agentway_leads.cli sync-sheets
```

5. Then verify:
   - admin UI shows templates, pending approvals, and leads
   - Google Sheet tabs are `Leads`, `Email Events`, `Meeting Notes`
   - new HubSpot submissions create Slack approval notifications instead of sending automatically

## Expected templates

- `email_signup_confirmation`
- `demo_booking_confirmation`
- `post_demo_followup`

Templates are seeded, then edited in the admin UI.

## Approval flow

This project now uses an approval-first model:

1. New email submissions and demo bookings land in HubSpot.
2. Sync or webhook ingestion creates/updates a lead locally.
3. The app queues an `approval_request` instead of sending right away.
4. Slack receives an approval message with:
   - `Approve + Send`
   - `Open Admin`
5. Clicking the approval link sends the chosen template through Gmail.

Important:

- `AUTOMATIC_EMAIL_ENABLED=false` should remain false unless the workflow is intentionally changed.
- Manual fallback still exists in `/admin`, but the primary operating model is Slack approval.

## Apps Script notes

The current Apps Script should:

- accept POST JSON with `sheet_id`, `tab_name`, `headers`, `rows`
- open the spreadsheet with `SpreadsheetApp.openById(sheetId)`
- reorder tabs so:
  - `Leads`
  - `Email Events`
  - `Meeting Notes`

The source of truth script in the repo is:

- `/Users/sabeen/Documents/Codex/2026-04-26/yes-i-think-you-can-and/apps_script/lead_sheet_sync.gs`

If the sheet order is wrong or sync breaks, repaste this file into Apps Script, redeploy, update `SHEETS_APPS_SCRIPT_URL`, then rerun `sync-sheets`.

## Common failure modes

- Admin page crashes:
  - check Railway logs
  - common cause was `None` first/last name in lead data
- Sheet sync succeeds but tabs/order are stale:
  - wrong Apps Script deployment URL
  - old Apps Script code still deployed
- Railway admin shows no leads/templates:
  - DB was never initialized or seeded
  - SQLite reset because no persistent volume is attached
- Slack approval arrives but email does not send:
  - Gmail OAuth vars are missing or stale
  - `EMAIL_PROVIDER` is not set to `gmail`
- New lead syncs but no Slack message appears:
  - `SLACK_WEBHOOK_URL` missing or invalid
  - no approval request generated for that lead type
- `sync-hubspot` returns `0 leads`:
  - wrong token
  - lead not in HubSpot
  - properties missing or access issue
- Exact ad activity string missing:
  - HubSpot may not expose the full timeline text as a contact property
  - use `ad_activity`, `ad_campaign_name`, `source_drilldown_*`, and `facebook_click_id`

## Ad attribution expectations

The lead model now stores:

- `source`
- `source_drilldown_1`
- `source_drilldown_2`
- `utm_campaign`
- `utm_ad`
- `utm_content`
- `ad_activity`
- `ad_campaign_name`
- `ad_campaign_id`
- `ad_group_id`
- `ad_id`
- `ad_network`
- `facebook_click_id`

Use `ad_activity` as the best available “exact ad” field from contact properties. It currently prefers `utm_content`, then falls back to HubSpot source drill-down data.

## Persistent datastore

This service should use a Railway volume mounted at `/data`, with:

```bash
DATABASE_PATH=/data/agentway_leads.db
```

If deploys keep clearing templates or leads, the volume is missing or not mounted correctly.

## Current env expectations

Prefer these vars for the live workflow:

```bash
EMAIL_PROVIDER=gmail
EMAIL_FROM_NAME=Sabeen
EMAIL_FROM_EMAIL=sabeen@agentway.com
GMAIL_ACCESS_TOKEN=
GMAIL_REFRESH_TOKEN=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REPLY_TO_EMAIL=sabeen@agentway.com
GMAIL_USER_ID=me
SLACK_WEBHOOK_URL=
ADMIN_TOKEN=43046721
AUTOMATIC_EMAIL_ENABLED=false
DATABASE_PATH=/data/agentway_leads.db
```
