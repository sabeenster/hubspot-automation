import tempfile
import unittest
from pathlib import Path

from src.agentway_leads.automation import (
    create_due_drafts,
    determine_automations,
    queue_approval_requests,
)
from src.agentway_leads.database import Database
from src.agentway_leads.email_sender import BaseEmailClient
from src.agentway_leads.models import Lead, Template


class FakeDraftClient(BaseEmailClient):
    def __init__(self):
        self.calls = []

    def create_draft(
        self,
        to_email,
        subject,
        body,
        event_id,
        dry_run=False,
    ):
        self.calls.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "event_id": event_id,
                "dry_run": dry_run,
            }
        )
        return {
            "id": "gmail-message-123",
            "threadId": "gmail-thread-123",
            "provider": "gmail_draft",
        }


class DraftAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.temp_dir.name) / "leads.db"))
        self.db.init_db()
        self.db.upsert_template(
            Template(
                template_name="email_signup_confirmation",
                lead_type="newsletter_signup",
                subject="Thanks, {{first_name}}",
                body="Hi {{first_name}},\n\nThanks for your interest.",
                delay_days=0,
                delay_minutes=0,
            )
        )
        self.db.upsert_lead(
            Lead(
                lead_id="lead-1",
                created_at="2026-07-27T12:00:00Z",
                first_name="Taylor",
                last_name="Example",
                email="taylor@example.com",
                lead_type="newsletter_signup",
                status="new",
            )
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_due_request_creates_one_draft_without_marking_email_sent(self):
        decisions = determine_automations(self.db.get_leads())
        queued = queue_approval_requests(self.db, decisions)
        self.assertEqual(len(queued), 1)

        client = FakeDraftClient()
        created = create_due_drafts(self.db, client)

        self.assertEqual(len(created), 1)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["to_email"], "taylor@example.com")
        self.assertIn("Taylor", client.calls[0]["subject"])

        event = self.db.get_email_events()[0]
        self.assertTrue(event.draft_created_at)
        self.assertEqual(event.sent_at, "")
        self.assertEqual(event.email_provider, "gmail_draft")

        request = self.db.get_approval_request(queued[0].approval_request_id)
        self.assertEqual(request.status, "drafted")
        self.assertTrue(request.draft_created_at)
        self.assertEqual(request.sent_at, "")

        lead = self.db.get_lead_by_id("lead-1")
        self.assertEqual(lead.last_email_drafted, "email_signup_confirmation")
        self.assertEqual(lead.confirmation_email_drafted, 1)
        self.assertEqual(lead.confirmation_email_sent, 0)
        self.assertEqual(lead.last_email_sent, "")

        self.assertEqual(determine_automations(self.db.get_leads()), [])
        self.assertEqual(create_due_drafts(self.db, client), [])
        self.assertEqual(len(client.calls), 1)

        # A later HubSpot refresh must not reset Agentway's draft state.
        self.db.upsert_lead(
            Lead(
                lead_id="lead-1",
                created_at="2026-07-27T12:00:00Z",
                first_name="Taylor",
                last_name="Updated",
                email="taylor@example.com",
                lead_type="newsletter_signup",
                status="new",
            )
        )
        refreshed = self.db.get_lead_by_id("lead-1")
        self.assertEqual(refreshed.last_name, "Updated")
        self.assertEqual(refreshed.confirmation_email_drafted, 1)
        self.assertEqual(refreshed.last_email_drafted, "email_signup_confirmation")
        self.assertEqual(determine_automations(self.db.get_leads()), [])


if __name__ == "__main__":
    unittest.main()
