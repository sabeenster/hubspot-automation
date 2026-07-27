# Agentway GTM Follow-up Roadmap

## Phase 1: Drafting

- HubSpot remains the lead and attribution source.
- Agentway evaluates approved templates and delays.
- Gmail drafts are created in `sabeen@agentway-ai.com`.
- Slack announces completed drafts.
- Sabeen reviews and manually sends.
- Draft creation and sent state remain separate.
- Open and click tracking continue to use the Railway tracking service.

Exit criteria:

- Unit and dry-run tests pass.
- Gmail integration contains no send endpoint.
- One internal draft succeeds with correct headers and tracking.
- Duplicate webhooks do not create duplicate drafts.
- Railway database persists through deployment.

## Phase 2: Follow-up intelligence

- Detect actual manual sends from HubSpot email activity.
- Detect replies, demo bookings, unsubscribes, and disqualification.
- Create later follow-up drafts only after the previous email was sent.
- Add email-signup and demo cadences.
- Report draft, sent, click, reply, and meeting conversion by Meta attribution.

## Phase 3: Optional sending

- Add explicit send controls for `sabeen@agentway-ai.com`.
- Keep `sabeen@agentway.com` out of scope until the test mailbox is proven.
- Add daily caps, suppression checks, retries, bounce handling, and audit logs.
- Test all sending paths internally before enabling any live automation.
