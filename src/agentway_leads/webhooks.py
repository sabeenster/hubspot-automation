import base64
import hashlib
import hmac
import json
import time
from typing import List

from .automation import create_due_drafts, determine_automations, queue_approval_requests
from .database import Database
from .email_sender import BaseEmailClient
from .hubspot import HubSpotClient, contact_to_lead
from .slack import SlackNotifier


def verify_hubspot_signature(
    body: bytes,
    secret: str,
    signature: str = "",
    signature_v3: str = "",
    timestamp: str = "",
    method: str = "POST",
    uri: str = "",
) -> bool:
    if not secret:
        return True
    if signature_v3:
        try:
            request_time_ms = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(int(time.time() * 1000) - request_time_ms) > 5 * 60 * 1000:
            return False
        normalized_uri = normalize_hubspot_signature_uri(uri)
        source = (
            method.upper().encode("utf-8")
            + normalized_uri.encode("utf-8")
            + body
            + timestamp.encode("utf-8")
        )
        digest = hmac.new(secret.encode("utf-8"), source, hashlib.sha256).digest()
        expected_v3 = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(expected_v3, signature_v3)
    if not signature:
        return False
    expected_v1 = hashlib.sha256(secret.encode("utf-8") + body).hexdigest()
    return hmac.compare_digest(expected_v1, signature)


def normalize_hubspot_signature_uri(uri: str) -> str:
    replacements = {
        "%3A": ":",
        "%2F": "/",
        "%3F": "?",
        "%40": "@",
        "%21": "!",
        "%24": "$",
        "%27": "'",
        "%28": "(",
        "%29": ")",
        "%2A": "*",
        "%2C": ",",
        "%3B": ";",
    }
    normalized = uri
    for encoded, decoded in replacements.items():
        normalized = normalized.replace(encoded, decoded).replace(
            encoded.lower(),
            decoded,
        )
    return normalized


def ingest_hubspot_webhook(
    db: Database,
    hubspot_client: HubSpotClient,
    slack_notifier: SlackNotifier,
    email_client: BaseEmailClient,
    automatic_draft_enabled: bool,
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
        queue_approval_requests(db, decisions)
        if automatic_draft_enabled:
            create_due_drafts(db, email_client, slack_notifier)
    return ingested
