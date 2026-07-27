import base64
import json
import unittest
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

from src.agentway_leads.email_sender import GmailEmailClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps({"id": "gmail-message-123", "threadId": "thread-123"}).encode()


class GmailDraftClientTests(unittest.TestCase):
    def test_create_draft_uses_insert_endpoint_and_draft_label(self):
        client = GmailEmailClient(
            access_token="test-token",
            from_name="Sabeen",
            from_email="sabeen@agentway-ai.com",
            tracking_base_url="https://automation.example.com",
            reply_to_email="sabeen@agentway-ai.com",
            bcc_email="12345@bcc.hubspot.com",
        )

        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("src.agentway_leads.email_sender.urlopen", fake_urlopen):
            result = client.create_draft(
                "lead@example.com",
                "Agentway follow-up",
                "Hi Taylor,\n\nSee https://agentway.ai",
                event_id="event-123",
            )

        request = captured["request"]
        self.assertEqual(
            request.full_url,
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        )
        self.assertNotIn("/send", request.full_url)
        self.assertEqual(request.get_method(), "POST")

        payload = json.loads(request.data.decode())
        self.assertEqual(payload["labelIds"], ["DRAFT"])
        message_bytes = base64.urlsafe_b64decode(payload["raw"].encode())
        message = BytesParser(policy=policy.default).parsebytes(message_bytes)
        self.assertEqual(message["To"], "lead@example.com")
        self.assertEqual(message["From"], "Sabeen <sabeen@agentway-ai.com>")
        self.assertEqual(message["Bcc"], "12345@bcc.hubspot.com")
        self.assertEqual(message["Reply-To"], "sabeen@agentway-ai.com")
        self.assertEqual(message["Subject"], "Agentway follow-up")
        html_part = message.get_body(preferencelist=("html",))
        self.assertIsNotNone(html_part)
        html = html_part.get_content()
        self.assertIn("/email/open?event_id=event-123", html)
        self.assertIn("/r?event_id=event-123", html)
        self.assertEqual(result["provider"], "gmail_draft")

    def test_missing_credentials_fails_instead_of_recording_a_fake_draft(self):
        client = GmailEmailClient(
            access_token="",
            from_name="Sabeen",
            from_email="sabeen@agentway-ai.com",
            tracking_base_url="https://automation.example.com",
        )
        with self.assertRaisesRegex(RuntimeError, "credentials are not configured"):
            client.create_draft(
                "lead@example.com",
                "Subject",
                "Body",
                event_id="event-123",
            )


if __name__ == "__main__":
    unittest.main()
