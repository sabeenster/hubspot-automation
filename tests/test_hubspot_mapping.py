import unittest

from src.agentway_leads.hubspot import contact_to_lead


class HubSpotMappingTests(unittest.TestCase):
    def test_meetings_contact_becomes_demo_request(self):
        lead = contact_to_lead(
            {
                "id": "contact-1",
                "properties": {
                    "createdate": "2026-07-22T11:26:46Z",
                    "firstname": "Ashley",
                    "lastname": "Ortega",
                    "email": "ashley@example.com",
                    "hs_object_source_label": "MEETINGS",
                    "recent_conversion_event_name": "Meetings Link: sabeen-minns",
                    "engagements_last_meeting_booked": "2026-07-27T17:15:00Z",
                    "hs_analytics_source": "PAID_SOCIAL",
                },
            }
        )
        self.assertEqual(lead.lead_type, "demo_request")
        self.assertEqual(lead.status, "demo_booked")
        self.assertEqual(lead.demo_booked_date, "2026-07-27T17:15:00Z")

    def test_ops_audit_form_becomes_email_signup(self):
        lead = contact_to_lead(
            {
                "id": "contact-2",
                "properties": {
                    "createdate": "2026-07-27T03:07:53Z",
                    "email": "signup@example.com",
                    "hs_object_source_label": "FORM",
                    "recent_conversion_event_name": "AI ops audit: Hupspot 041426",
                    "hs_analytics_source": "PAID_SOCIAL",
                },
            }
        )
        self.assertEqual(lead.lead_type, "newsletter_signup")
        self.assertEqual(lead.status, "new")


if __name__ == "__main__":
    unittest.main()
