import json
import re
import uuid
from html import escape
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


URL_RE = re.compile(r"(https?://[^\s]+)")


class ResendEmailClient:
    def __init__(
        self,
        api_key: str,
        from_name: str,
        from_email: str,
        tracking_base_url: str,
        reply_to_email: str = "",
    ):
        self.api_key = api_key
        self.from_name = from_name
        self.from_email = from_email
        self.tracking_base_url = tracking_base_url.rstrip("/")
        self.reply_to_email = reply_to_email

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        event_id: str,
        dry_run: bool = False,
    ) -> Dict[str, str]:
        if dry_run or not self.api_key:
            return {
                "id": f"dryrun-{uuid.uuid4()}",
                "provider": "resend",
            }

        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
            "html": render_html_email(body, self.tracking_base_url, event_id),
            "tags": [
                {"name": "event_id", "value": event_id},
                {"name": "source", "value": "agentway"},
            ],
        }
        if self.reply_to_email:
            payload["reply_to"] = self.reply_to_email

        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "id": data.get("id", ""),
                    "provider": "resend",
                }
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Resend send failed: {exc}") from exc

    def detect_reply(self, provider_message_id: str) -> bool:
        # Placeholder for future reply detection, likely via inbound webhooks.
        return False


def render_html_email(body: str, tracking_base_url: str, event_id: str) -> str:
    safe_text = escape(body)
    linked = URL_RE.sub(
        lambda match: build_tracked_anchor(match.group(1), tracking_base_url, event_id),
        safe_text,
    )
    html_body = linked.replace("\n\n", "</p><p>").replace("\n", "<br>")
    pixel_url = f"{tracking_base_url}/email/open?event_id={quote(event_id)}"
    return f"<p>{html_body}</p><img src=\"{pixel_url}\" width=\"1\" height=\"1\" alt=\"\" />"


def build_tracked_anchor(url: str, tracking_base_url: str, event_id: str) -> str:
    tracked_url = f"{tracking_base_url}/r?event_id={quote(event_id)}&url={quote(url, safe='')}"
    return f'<a href="{tracked_url}">{url}</a>'
