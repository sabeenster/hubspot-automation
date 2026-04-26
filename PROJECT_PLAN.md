# Agentway Lead Automation Plan

Last updated: 2026-04-26

## Current objective

Build a lightweight Agentway-owned automation layer that uses:

- HubSpot for lead capture and attribution
- Gmail for outbound sending
- Google Sheets for visibility and lightweight ops CRM
- Granola for meeting-note linkage

## Current status

Completed:

- Local Python project scaffold created
- SQLite lead/email/meeting-note store created
- HubSpot sync CLI added
- HubSpot webhook endpoint added
- Gmail send path added
- Open/click tracking endpoints added
- Granola note sync and lead linkage added
- HubSpot attribution fields expanded for future ad-aware personalization
- Local git repo initialized and connected to `https://github.com/sabeenster/hubspot-automation.git`
- Railway deployment config added for a hosted webhook/tracking service

In progress:

- Tighten live integration behavior and setup docs
- Deploy to Railway and document service/cron setup

Next:

1. Add reply detection path from Gmail thread IDs
2. Improve HubSpot webhook ingestion for real payload variants
3. Document deployment and auth steps
4. Deploy to Railway and verify live health/webhook routes
5. Add scheduled Railway job for `sync-all`

## Important design decisions

- HubSpot remains the CRM of record and attribution source.
- Automation logic lives outside HubSpot.
- MailSuite is supplemental analytics, not the system of record.
- Granola is polled rather than webhook-driven.
- Lead attribution data should be stored both in normalized fields and raw HubSpot snapshot form.

## Notes for resumed sessions

- The active project root is this folder.
- The intended GitHub remote is `origin = sabeenster/hubspot-automation`.
- Do not use the unrelated parent repo rooted at `/Users/sabeen`.
- If pushing fails, the user may need to complete GitHub auth in the web UI.
