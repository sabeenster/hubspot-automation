import hashlib
import hmac
import json
from typing import List

from .database import Database
from .hubspot import contact_to_lead


def verify_hubspot_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def ingest_hubspot_webhook(db: Database, body: bytes) -> int:
    payload = json.loads(body.decode("utf-8"))
    contacts: List[dict] = payload if isinstance(payload, list) else payload.get("contacts", [])
    ingested = 0
    for contact in contacts:
        if not contact.get("properties", {}).get("email"):
            continue
        db.upsert_lead(contact_to_lead(contact))
        ingested += 1
    return ingested
