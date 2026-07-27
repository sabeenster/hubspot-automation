import json
import secrets
import uuid
from datetime import timedelta
from typing import List, Optional

from .database import Database
from .email_sender import BaseEmailClient
from .models import (
    ApprovalRequest,
    AutomationDecision,
    EmailEvent,
    Lead,
    Template,
    parse_iso_datetime,
    utcnow_iso,
)
from .slack import SlackNotifier
from .templates import render_template


def determine_automations(leads: List[Lead]) -> List[AutomationDecision]:
    decisions: List[AutomationDecision] = []
    for lead in leads:
        if lead.unsubscribed:
            continue
        if (
            lead.lead_type in {"newsletter_signup", "contact_form"}
            and not lead.confirmation_email_sent
            and not lead.confirmation_email_drafted
            and lead.status in {"new", "nurture"}
        ):
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="email_signup_confirmation",
                    reason="new lead confirmation ready to draft",
                    context={"first_name": lead.first_name or "there"},
                )
            )
        if (
            lead.lead_type == "demo_request"
            and not lead.demo_confirmation_sent
            and not lead.demo_confirmation_drafted
        ):
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="demo_booking_confirmation",
                    reason="demo booking confirmation ready to draft",
                    context={"first_name": lead.first_name or "there"},
                )
            )
        if (
            lead.status == "demo_completed"
            and not lead.post_demo_followup_sent
            and not lead.post_demo_followup_drafted
        ):
            decisions.append(
                AutomationDecision(
                    lead_id=lead.lead_id,
                    template_name="post_demo_followup",
                    reason="post-demo follow-up ready to draft",
                    context={
                        "first_name": lead.first_name or "there",
                        "workflow_area": lead.workflow_area or "your current workflow",
                    },
                )
            )
    return decisions


def queue_approval_requests(
    db: Database,
    decisions: List[AutomationDecision],
) -> List[ApprovalRequest]:
    queued: List[ApprovalRequest] = []
    for decision in decisions:
        lead = db.get_lead_by_id(decision.lead_id)
        template = db.get_template(decision.template_name)
        if not lead or not template:
            continue
        existing = db.get_approval_request_for_lead_template(lead.lead_id, template.template_name)
        if existing and existing.status in {
            "pending",
            "notified",
            "approved",
            "drafted",
            "sent",
        }:
            continue
        request = ApprovalRequest(
            approval_request_id=existing.approval_request_id if existing else str(uuid.uuid4()),
            lead_id=lead.lead_id,
            template_name=template.template_name,
            approval_token=existing.approval_token if existing else secrets.token_urlsafe(24),
            status="pending",
            reason=decision.reason,
            context_json=json.dumps(decision.context, sort_keys=True),
            requested_at=utcnow_iso(),
            notified_at="",
            draft_created_at="",
            approved_at="",
            sent_at="",
            failed_at="",
            failure_reason="",
        )
        db.upsert_approval_request(request)
        queued.append(request)
    return queued


def create_request_draft(
    db: Database,
    email_client: BaseEmailClient,
    approval_request_id: str,
    approval_token: str = "",
    slack_notifier: Optional[SlackNotifier] = None,
    dry_run: bool = False,
) -> EmailEvent:
    approval_request = db.get_approval_request(approval_request_id)
    if not approval_request:
        raise ValueError("Approval request not found")
    if approval_token and approval_request.approval_token != approval_token:
        raise ValueError("Invalid approval token")
    if approval_request.status in {"drafted", "sent"}:
        raise ValueError("Draft already created")
    lead = db.get_lead_by_id(approval_request.lead_id)
    template = db.get_template(approval_request.template_name)
    if not lead or not template:
        raise ValueError("Lead or template missing")
    context = json.loads(approval_request.context_json or "{}")
    try:
        event = create_template_draft(
            db,
            email_client,
            lead,
            template,
            context,
            dry_run=dry_run,
        )
        if dry_run:
            return event
        created_at = event.draft_created_at
        db.update_approval_request_fields(
            approval_request_id,
            status="drafted",
            draft_created_at=created_at,
            failure_reason="",
        )
        if slack_notifier:
            notified = slack_notifier.send_draft_ready(
                approval_request,
                lead,
                template,
                event.gmail_message_id,
            )
            if notified:
                db.update_approval_request_fields(
                    approval_request_id,
                    notified_at=utcnow_iso(),
                )
        return event
    except Exception as exc:
        db.update_approval_request_fields(
            approval_request_id,
            status="failed",
            failed_at=utcnow_iso(),
            failure_reason=str(exc),
        )
        raise


def create_draft_for_lead(
    db: Database,
    email_client: BaseEmailClient,
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
    pending_request = db.get_approval_request_for_lead_template(
        lead.lead_id,
        template_name,
    )
    if pending_request and pending_request.status in {"pending", "failed"}:
        return create_request_draft(
            db,
            email_client,
            pending_request.approval_request_id,
            dry_run=dry_run,
        )
    template = db.get_template(template_name)
    if not template:
        raise ValueError("Template not found")
    context = {
        "first_name": lead.first_name or "there",
        "workflow_area": lead.workflow_area or "your current workflow",
    }
    return create_template_draft(db, email_client, lead, template, context, dry_run=dry_run)


def create_template_draft(
    db: Database,
    email_client: BaseEmailClient,
    lead: Lead,
    template: Template,
    context: dict,
    dry_run: bool = False,
) -> EmailEvent:
    subject = render_template(template.subject, context)
    body = render_template(template.body, context)
    email_event_id = str(uuid.uuid4())
    response = email_client.create_draft(
        lead.email,
        subject,
        body,
        event_id=email_event_id,
        dry_run=dry_run,
    )
    provider_message_id = response.get("id", "")
    created_at = utcnow_iso()
    event = EmailEvent(
        email_event_id=email_event_id,
        lead_id=lead.lead_id,
        email=lead.email,
        template_name=template.template_name,
        subject=subject,
        draft_created_at=created_at,
        sent_at="",
        email_provider=response.get("provider", "gmail_draft"),
        provider_message_id=provider_message_id,
        gmail_message_id=provider_message_id
        if response.get("provider") == "gmail_draft"
        else "",
        gmail_thread_id=response.get("threadId", ""),
    )
    if dry_run:
        return event
    db.insert_email_event(event)
    update_lead_after_draft(db, lead, template.template_name)
    return event


def create_due_drafts(
    db: Database,
    email_client: BaseEmailClient,
    slack_notifier: Optional[SlackNotifier] = None,
    dry_run: bool = False,
) -> List[EmailEvent]:
    created: List[EmailEvent] = []
    requests = db.get_approval_requests(status="pending")
    for request in requests:
        lead = db.get_lead_by_id(request.lead_id)
        template = db.get_template(request.template_name)
        if not lead or not template or not is_due_to_draft(lead, template):
            continue
        created.append(
            create_request_draft(
                db,
                email_client,
                request.approval_request_id,
                slack_notifier=slack_notifier,
                dry_run=dry_run,
            )
        )
    return created


def is_due_to_draft(lead: Lead, template: Template) -> bool:
    now = parse_iso_datetime(utcnow_iso())
    anchor = scheduled_from_timestamp(lead, template)
    delay = timedelta(days=template.delay_days, minutes=template.delay_minutes)
    return now >= anchor + delay


def is_due_to_send(lead: Lead, template: Template) -> bool:
    """Backward-compatible alias for older callers."""
    return is_due_to_draft(lead, template)


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


def update_lead_after_draft(db: Database, lead: Lead, template_name: str) -> None:
    if template_name == "email_signup_confirmation":
        db.update_lead_fields(
            lead.lead_id,
            last_email_drafted=template_name,
            confirmation_email_drafted=1,
        )
    elif template_name == "demo_booking_confirmation":
        db.update_lead_fields(
            lead.lead_id,
            last_email_drafted=template_name,
            demo_confirmation_drafted=1,
        )
    elif template_name == "post_demo_followup":
        db.update_lead_fields(
            lead.lead_id,
            last_email_drafted=template_name,
            post_demo_followup_drafted=1,
        )
