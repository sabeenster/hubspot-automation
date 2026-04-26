import json
import uuid
from pathlib import Path
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .database import Database
from .models import MeetingNote


class GranolaClient:
    def __init__(self, api_key: str, api_base: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    def fetch_notes(self) -> List[dict]:
        if not self.api_key:
            return []
        request = Request(
            f"{self.api_base}/v1/notes",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError):
            return []
        return payload.get("data", [])

    def load_sample_notes(self, path: str) -> List[dict]:
        return json.loads(Path(path).read_text())


def sync_granola_notes(db: Database, notes: List[dict]) -> int:
    linked = 0
    for note in notes:
        attendees = note.get("attendees", [])
        matched_lead = None
        for attendee in attendees:
            email = (attendee.get("email") or "").strip().lower()
            if not email:
                continue
            matched_lead = db.get_lead_by_email(email)
            if matched_lead:
                break
        if not matched_lead:
            continue

        meeting_note = MeetingNote(
            meeting_note_id=str(uuid.uuid4()),
            lead_id=matched_lead.lead_id,
            external_id=note.get("id", str(uuid.uuid4())),
            title=note.get("title", "Customer meeting"),
            note_url=note.get("url", ""),
            note_summary=note.get("summary", ""),
            meeting_at=note.get("meeting_at", note.get("created_at", "")),
        )
        db.upsert_meeting_note(meeting_note)
        db.update_lead_fields(
            matched_lead.lead_id,
            last_meeting_at=meeting_note.meeting_at,
            granola_note_url=meeting_note.note_url,
            granola_note_summary=meeting_note.note_summary,
        )
        linked += 1
    return linked
