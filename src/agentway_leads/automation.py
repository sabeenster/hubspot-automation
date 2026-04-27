import uuid
from datetime import timedelta
from typing import List

from .database import Database
from .email_sender import ResendEmailClient
from .models import AutomationDecision, EmailEvent, Lead, Template, parse_iso_datetime, utcnow_iso
from .templates import render_template


def determine_automations(leads: List[Lead]) -> List[AutomationDecision]:
    decisions: List[AutomationDecision] = []
    for lead in leads:
        if lead.unsubscribed:
            continue
        if (
            lead.lead_type in {"newsletter_signup", "contact_form"}
            and not lead.confirmation_email_sent
            and lead.status in {"new", "nurture"}
        ):
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="email_signup_confirmation",
                    reason="new lead confirmation after delay",
                    context={"first_name": lead.first_name or "there"},
                )
            )
        if lead.lead_type == "demo_request" and not lead.demo_confirmation_sent:
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="demo_booking_confirmation",
                    reason="demo booked confirmation after delay",
                    context={"first_name": lead.first_name or "there"},
                )
            )
        if lead.status == "demo_completed" and not lead.post_demo_followup_sent:
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="post_demo_followup",
                    reason="post demo follow-up",
                    context={
                        "first_name": lead.first_name or "there",
                        "workflow_area": lead.workflow_area or "your current workflow",
                    },
                )
            )
    return decisions


def execute_automations(
    db: Database,
    email_client: ResendEmailClient,
    decisions: List[AutomationDecision],
    automatic_email_enabled: bool = True,
    dry_run: bool = False,
) -> List[EmailEvent]:
    sent: List[EmailEvent] = []
    if not automatic_email_enabled and not dry_run:
        return sent
    for decision in decisions:
        lead = db.get_lead_by_id(decision.lead_id)
        template = db.get_template(decision.template_name)
        if not lead or not template:
            continue
        if not is_due_to_send(lead, template):
            continue
        event = send_template_to_lead(
            db,
            email_client,
            lead,
            template,
            decision.context,
            dry_run=dry_run,
        )
        sent.append(event)
    return sent


def send_confirmation_for_lead(
    db: Database,
    email_client: ResendEmailClient,
    lead_id: str,
    template_name: str = "",
    dry_run: bool = False,
) -> EmailEvent:
    lead = db.get_lead_by_id(lead_id)
    if not lead:
        raise ValueError("Lead not found")
    template_name = template_name or recommended_confirmation_template_name(lead)
    if not template_name:
        raise ValueError("No confirmation template for this lead")
    template = db.get_template(template_name)
    if not template:
        raise ValueError("Template not found")
    context = {
        "first_name": lead.first_name or "there",
        "workflow_area": lead.workflow_area or "your current workflow",
    }
    return send_template_to_lead(db, email_client, lead, template, context, dry_run=dry_run)


def send_template_to_lead(
    db: Database,
    email_client: ResendEmailClient,
    lead: Lead,
    template: Template,
    context: dict,
    dry_run: bool = False,
) -> EmailEvent:
    subject = render_template(template.subject, context)
    body = render_template(template.body, context)
    email_event_id = str(uuid.uuid4())
    response = email_client.send_email(
        lead.email,
        subject,
        body,
        event_id=email_event_id,
        dry_run=dry_run,
    )
    event = EmailEvent(
        email_event_id=email_event_id,
        lead_id=lead.lead_id,
        email=lead.email,
        template_name=template.template_name,
        subject=subject,
        sent_at=utcnow_iso(),
        email_provider=response.get("provider", "resend"),
        provider_message_id=response.get("id", ""),
        gmail_message_id=response.get("id", ""),
        gmail_thread_id=response.get("threadId", ""),
    )
    db.insert_email_event(event)
    update_lead_after_send(db, lead, template.template_name)
    return event


def is_due_to_send(lead: Lead, template: Template) -> bool:
    now = parse_iso_datetime(utcnow_iso())
    anchor = scheduled_from_timestamp(lead, template)
    delay = timedelta(days=template.delay_days, minutes=template.delay_minutes)
    return now >= anchor + delay


def scheduled_from_timestamp(lead: Lead, template: Template):
    if template.template_name == "demo_booking_confirmation" and lead.demo_booked_date:
        return parse_iso_datetime(lead.demo_booked_date)
    return parse_iso_datetime(lead.created_at)


def recommended_confirmation_template_name(lead: Lead) -> str:
    if lead.lead_type in {"newsletter_signup", "contact_form"}:
        return "email_signup_confirmation"
    if lead.lead_type == "demo_request":
        return "demo_booking_confirmation"
    return ""


def update_lead_after_send(db: Database, lead: Lead, template_name: str) -> None:
    if template_name == "email_signup_confirmation":
        db.update_lead_fields(
            lead.lead_id,
            status="confirmed",
            last_email_sent=template_name,
            confirmation_email_sent=1,
        )
    elif template_name == "demo_booking_confirmation":
        db.update_lead_fields(
            lead.lead_id,
            status="demo_booked",
            last_email_sent=template_name,
            demo_confirmation_sent=1,
        )
    elif template_name == "post_demo_followup":
        db.update_lead_fields(
            lead.lead_id,
            last_email_sent=template_name,
            post_demo_followup_sent=1,
        )
