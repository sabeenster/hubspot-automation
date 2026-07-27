from collections import Counter
from typing import Dict

from .database import Database


def generate_weekly_report(db: Database) -> Dict[str, object]:
    leads = db.get_leads()
    events = db.get_email_events()
    meeting_notes = db.get_meeting_notes()

    status_counts = Counter(lead.status for lead in leads)
    source_counts = Counter(lead.source or "unknown" for lead in leads)

    return {
        "new_leads": sum(1 for lead in leads if lead.status == "new"),
        "demo_requests": sum(1 for lead in leads if lead.lead_type == "demo_request"),
        "demo_completed": sum(1 for lead in leads if lead.status == "demo_completed"),
        "no_shows": sum(1 for lead in leads if lead.status == "no_show"),
        "replies": sum(1 for event in events if event.replied_at),
        "drafts_created": sum(1 for event in events if event.draft_created_at),
        "emails_sent": sum(1 for event in events if event.sent_at),
        "email_clicks": sum(1 for event in events if event.clicked_at),
        "qualified_leads": sum(1 for lead in leads if lead.status == "qualified"),
        "meetings_linked": len(meeting_notes),
        "top_sources": source_counts.most_common(5),
        "statuses": status_counts,
        "manual_follow_ups_needed": sum(
            1 for lead in leads if lead.next_step and lead.status not in {"qualified", "not_a_fit"}
        ),
    }
