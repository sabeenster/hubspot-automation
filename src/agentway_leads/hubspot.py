import json
from pathlib import Path
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

from .models import Lead, utcnow_iso


class HubSpotClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def fetch_recent_contacts(self, limit: int = 100) -> List[dict]:
        if not self.access_token:
            return []
        query = urlencode({"limit": limit, "properties": ",".join(HUBSPOT_CONTACT_PROPERTIES)})
        request = Request(
            "https://api.hubapi.com/crm/v3/objects/contacts?" + query,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError):
            return []
        return payload.get("results", [])

    def load_sample_contacts(self, path: str) -> List[dict]:
        return json.loads(Path(path).read_text())


def contact_to_lead(contact: dict) -> Lead:
    props = contact.get("properties", {})
    email = props.get("email", "").strip().lower()
    lead_type = infer_lead_type(props)
    attribution = extract_attribution(props)
    status = "demo_booked" if lead_type == "demo_request" else "new"
    return Lead(
        lead_id=contact.get("id") or str(uuid.uuid4()),
        created_at=props.get("createdate", utcnow_iso()),
        first_name=props.get("firstname", "") or "there",
        last_name=props.get("lastname", ""),
        email=email,
        company=props.get("company", ""),
        job_title=props.get("jobtitle", ""),
        source=attribution["source"],
        source_drilldown_1=attribution["source_drilldown_1"],
        source_drilldown_2=attribution["source_drilldown_2"],
        utm_campaign=attribution["utm_campaign"],
        utm_ad=attribution["utm_ad"],
        utm_content=attribution["utm_content"],
        ad_activity=attribution["ad_activity"],
        ad_campaign_name=attribution["ad_campaign_name"],
        ad_campaign_id=attribution["ad_campaign_id"],
        ad_group_id=attribution["ad_group_id"],
        ad_id=attribution["ad_id"],
        ad_network=attribution["ad_network"],
        facebook_click_id=attribution["facebook_click_id"],
        attribution_snapshot_json=attribution["attribution_snapshot_json"],
        hubspot_contact_id=contact.get("id", ""),
        lead_type=lead_type,
        status=status,
        lifecycle_stage=props.get("lifecyclestage", ""),
        demo_booked_date=props.get("demo_booked_date", ""),
    )


def infer_lead_type(properties: dict) -> str:
    if properties.get("demo_booked_date"):
        return "demo_request"
    form_type = (properties.get("form_type") or "").lower()
    if "newsletter" in form_type or "email" in form_type:
        return "newsletter_signup"
    if "demo" in form_type:
        return "demo_request"
    if "contact" in form_type:
        return "contact_form"
    return "newsletter_signup"


HUBSPOT_CONTACT_PROPERTIES = [
    "createdate",
    "firstname",
    "lastname",
    "email",
    "company",
    "jobtitle",
    "lifecyclestage",
    "hs_lead_status",
    "form_type",
    "demo_booked_date",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "hs_analytics_source",
    "hs_analytics_source_data_1",
    "hs_analytics_source_data_2",
    "hs_latest_source",
    "hs_latest_source_data_1",
    "hs_latest_source_data_2",
    "hs_object_source",
    "hs_facebook_click_id",
]


def extract_attribution(properties: Dict[str, str]) -> Dict[str, str]:
    source = first_non_empty(
        properties.get("utm_source"),
        properties.get("hs_latest_source"),
        properties.get("hs_analytics_source"),
        properties.get("hs_object_source"),
    )
    source_drilldown_1 = first_non_empty(
        properties.get("hs_latest_source_data_1"),
        properties.get("hs_analytics_source_data_1"),
    )
    source_drilldown_2 = first_non_empty(
        properties.get("hs_latest_source_data_2"),
        properties.get("hs_analytics_source_data_2"),
    )
    ad_campaign_name = first_non_empty(
        properties.get("utm_campaign"),
        source_drilldown_1,
    )
    ad_activity = first_non_empty(
        properties.get("utm_content"),
        source_drilldown_2,
    )
    ad_campaign_id = read_hubspot_id(source_drilldown_1)
    ad_id = read_hubspot_id(source_drilldown_2)
    snapshot = {
        "utm_source": properties.get("utm_source", ""),
        "utm_medium": properties.get("utm_medium", ""),
        "utm_campaign": properties.get("utm_campaign", ""),
        "utm_content": properties.get("utm_content", ""),
        "hs_analytics_source": properties.get("hs_analytics_source", ""),
        "hs_analytics_source_data_1": properties.get("hs_analytics_source_data_1", ""),
        "hs_analytics_source_data_2": properties.get("hs_analytics_source_data_2", ""),
        "hs_latest_source": properties.get("hs_latest_source", ""),
        "hs_latest_source_data_1": properties.get("hs_latest_source_data_1", ""),
        "hs_latest_source_data_2": properties.get("hs_latest_source_data_2", ""),
        "hs_object_source": properties.get("hs_object_source", ""),
        "hs_facebook_click_id": properties.get("hs_facebook_click_id", ""),
    }
    return {
        "source": source,
        "source_drilldown_1": source_drilldown_1,
        "source_drilldown_2": source_drilldown_2,
        "utm_campaign": properties.get("utm_campaign", ""),
        "utm_ad": properties.get("utm_medium", ""),
        "utm_content": properties.get("utm_content", ""),
        "ad_activity": ad_activity,
        "ad_campaign_name": ad_campaign_name,
        "ad_campaign_id": ad_campaign_id,
        "ad_group_id": "",
        "ad_id": ad_id,
        "ad_network": normalize_ad_network(source),
        "facebook_click_id": properties.get("hs_facebook_click_id", ""),
        "attribution_snapshot_json": json.dumps(snapshot, sort_keys=True),
    }


def first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def read_hubspot_id(value: str) -> str:
    if not value:
        return ""
    return value if value.isdigit() else ""


def normalize_ad_network(source: str) -> str:
    lowered = source.lower()
    if "facebook" in lowered or "meta" in lowered:
        return "meta"
    if "google" in lowered:
        return "google"
    if "linkedin" in lowered:
        return "linkedin"
    return source
