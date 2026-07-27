import json
import urllib.request
from typing import Iterable, List

from .models import EmailEvent, Lead, MeetingNote

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - handled at runtime when deps are absent
    service_account = None
    build = None


LEADS_HEADERS = [
    "lead_id",
    "created_at",
    "first_name",
    "last_name",
    "email",
    "company",
    "job_title",
    "source",
    "source_drilldown_1",
    "source_drilldown_2",
    "utm_campaign",
    "utm_ad",
    "utm_content",
    "ad_activity",
    "ad_campaign_name",
    "ad_campaign_id",
    "ad_group_id",
    "ad_id",
    "ad_network",
    "facebook_click_id",
    "hubspot_contact_id",
    "lead_type",
    "status",
    "lifecycle_stage",
    "last_email_sent",
    "next_action_date",
    "demo_booked_date",
    "demo_completed",
    "last_meeting_at",
    "granola_note_url",
    "granola_note_summary",
    "notes",
    "owner",
    "lead_quality",
    "next_step",
    "confirmation_email_sent",
    "demo_confirmation_sent",
    "post_demo_followup_sent",
    "email_opt_in",
    "unsubscribed",
]

EMAIL_EVENTS_HEADERS = [
    "email_event_id",
    "lead_id",
    "email",
    "template_name",
    "subject",
    "sent_at",
    "email_provider",
    "provider_message_id",
    "gmail_message_id",
    "gmail_thread_id",
    "opened_at",
    "clicked_at",
    "replied_at",
    "clicked_url",
    "bounced",
    "unsubscribe_clicked",
]

MEETING_NOTES_HEADERS = [
    "meeting_note_id",
    "lead_id",
    "external_id",
    "title",
    "note_url",
    "note_summary",
    "meeting_at",
    "source",
]


class GoogleSheetsSync:
    def __init__(
        self,
        sheet_id: str,
        service_account_json: str,
        apps_script_webhook_url: str = "",
    ):
        self.sheet_id = sheet_id
        self.service_account_json = service_account_json
        self.apps_script_webhook_url = apps_script_webhook_url

    def push_leads(self, leads: Iterable[Lead]) -> None:
        rows = [
            [getattr(lead, header, "") for header in LEADS_HEADERS]
            for lead in leads
        ]
        self._write_tab("Leads", LEADS_HEADERS, rows)

    def push_email_events(self, events: Iterable[EmailEvent]) -> None:
        rows = [
            [getattr(event, header, "") for header in EMAIL_EVENTS_HEADERS]
            for event in events
        ]
        self._write_tab("Email Events", EMAIL_EVENTS_HEADERS, rows)

    def push_meeting_notes(self, notes: Iterable[MeetingNote]) -> None:
        rows = [
            [getattr(note, header, "") for header in MEETING_NOTES_HEADERS]
            for note in notes
        ]
        self._write_tab("Meeting Notes", MEETING_NOTES_HEADERS, rows)

    def _write_tab(self, tab_name: str, headers: List[str], rows: List[List[object]]) -> None:
        if self.apps_script_webhook_url:
            self._write_via_apps_script(tab_name, headers, rows)
            return
        service = self._build_service()
        payload = {
            "valueInputOption": "RAW",
            "data": [
                {
                    "range": f"{tab_name}!A1",
                    "values": [headers] + rows,
                }
            ],
        }
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.sheet_id,
            body=payload,
        ).execute()

    def _write_via_apps_script(
        self,
        tab_name: str,
        headers: List[str],
        rows: List[List[object]],
    ) -> None:
        payload = {
            "sheet_id": self.sheet_id,
            "tab_name": tab_name,
            "headers": headers,
            "rows": rows,
        }
        request = urllib.request.Request(
            self.apps_script_webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()

    def _build_service(self):
        if not self.sheet_id or not self.service_account_json:
            raise RuntimeError(
                "Google Sheets credentials are not configured. "
                "Set SHEETS_APPS_SCRIPT_URL for the simpler attached-sheet flow, "
                "or provide GOOGLE_SERVICE_ACCOUNT_JSON for the direct Sheets API flow."
            )
        if service_account is None or build is None:
            raise RuntimeError(
                "Google Sheets dependencies are not installed. Install requirements.txt first."
            )
        info = json.loads(self.service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)
