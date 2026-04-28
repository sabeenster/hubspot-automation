import hashlib
import hmac
import json
from typing import List

from .automation import determine_automations, queue_approval_requests
from .database import Database
from .hubspot import HubSpotClient, contact_to_lead
from .slack import SlackNotifier


def verify_hubspot_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def ingest_hubspot_webhook(
    db: Database,
    hubspot_client: HubSpotClient,
    slack_notifier: SlackNotifier,
    body: bytes,
) -> int:
    payload = json.loads(body.decode("utf-8"))
    events: List[dict] = payload if isinstance(payload, list) else payload.get("contacts", [])
    ingested = 0
    touched_lead_ids = []
    for event in events:
        if event.get("properties", {}).get("email"):
            contact = event
        else:
            object_id = str(event.get("objectId") or event.get("object_id") or "")
            contact = hubspot_client.fetch_contact(object_id)
        if not contact or not contact.get("properties", {}).get("email"):
            continue
        lead = contact_to_lead(contact)
        db.upsert_lead(lead)
        ingested += 1
        touched_lead_ids.append(lead.lead_id)

    if touched_lead_ids:
        leads = [db.get_lead_by_id(lead_id) for lead_id in touched_lead_ids]
        decisions = determine_automations([lead for lead in leads if lead])
        queue_approval_requests(db, decisions, slack_notifier)
    return ingested
