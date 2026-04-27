from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict


@dataclass
class Lead:
    lead_id: str
    created_at: str
    first_name: str
    last_name: str
    email: str
    company: str = ""
    job_title: str = ""
    source: str = ""
    source_drilldown_1: str = ""
    source_drilldown_2: str = ""
    utm_campaign: str = ""
    utm_ad: str = ""
    utm_content: str = ""
    ad_activity: str = ""
    ad_campaign_name: str = ""
    ad_campaign_id: str = ""
    ad_group_id: str = ""
    ad_id: str = ""
    ad_network: str = ""
    facebook_click_id: str = ""
    attribution_snapshot_json: str = ""
    hubspot_contact_id: str = ""
    lead_type: str = "manual_add"
    status: str = "new"
    lifecycle_stage: str = ""
    last_email_sent: str = ""
    next_action_date: str = ""
    demo_booked_date: str = ""
    demo_completed: int = 0
    notes: str = ""
    owner: str = ""
    lead_quality: str = ""
    next_step: str = ""
    confirmation_email_sent: int = 0
    demo_confirmation_sent: int = 0
    post_demo_followup_sent: int = 0
    email_opt_in: int = 1
    unsubscribed: int = 0
    workflow_area: str = "your current workflow"
    last_meeting_at: str = ""
    granola_note_url: str = ""
    granola_note_summary: str = ""


@dataclass
class Template:
    template_name: str
    lead_type: str
    subject: str
    body: str
    delay_days: int = 0
    delay_minutes: int = 0
    active: bool = True


@dataclass
class EmailEvent:
    email_event_id: str
    lead_id: str
    email: str
    template_name: str
    subject: str
    sent_at: str
    email_provider: str = "resend"
    provider_message_id: str = ""
    gmail_message_id: str = ""
    gmail_thread_id: str = ""
    opened_at: str = ""
    clicked_at: str = ""
    replied_at: str = ""
    clicked_url: str = ""
    bounced: int = 0
    unsubscribe_clicked: int = 0


@dataclass
class MeetingNote:
    meeting_note_id: str
    lead_id: str
    external_id: str
    title: str
    note_url: str
    note_summary: str
    meeting_at: str
    source: str = "granola"


@dataclass
class AutomationDecision:
    lead_id: str
    template_name: str
    reason: str
    context: Dict[str, str] = field(default_factory=dict)


def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def parse_iso_datetime(value: str) -> datetime:
    normalized = (value or "").strip()
    if not normalized:
        return datetime.now(timezone.utc)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
