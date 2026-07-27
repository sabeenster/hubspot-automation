import base64
import json
import re
import uuid
from email.message import EmailMessage
from html import escape
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


URL_RE = re.compile(r"(https?://[^\s]+)")


class BaseEmailClient:
    def create_draft(
        self,
        to_email: str,
        subject: str,
        body: str,
        event_id: str,
        dry_run: bool = False,
    ) -> Dict[str, str]:
        raise NotImplementedError

    def detect_reply(self, provider_message_id: str) -> bool:
        return False


class GmailEmailClient(BaseEmailClient):
    def __init__(
        self,
        access_token: str,
        from_name: str,
        from_email: str,
        tracking_base_url: str,
        reply_to_email: str = "",
        bcc_email: str = "",
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        user_id: str = "me",
    ):
        self.access_token = access_token
        self.from_name = from_name
        self.from_email = from_email
        self.tracking_base_url = tracking_base_url.rstrip("/")
        self.reply_to_email = reply_to_email
        self.bcc_email = bcc_email
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id

    def create_draft(
        self,
        to_email: str,
        subject: str,
        body: str,
        event_id: str,
        dry_run: bool = False,
    ) -> Dict[str, str]:
        if dry_run:
            return {
                "id": f"dryrun-{uuid.uuid4()}",
                "threadId": f"dryrun-thread-{uuid.uuid4()}",
                "provider": "gmail_draft",
            }
        token = self._access_token()
        if not token:
            raise RuntimeError(
                "Gmail draft credentials are not configured. "
                "Set a Gmail access token or refresh-token OAuth credentials."
            )

        message = EmailMessage()
        message["To"] = to_email
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["Subject"] = subject
        if self.reply_to_email:
            message["Reply-To"] = self.reply_to_email
        if self.bcc_email:
            message["Bcc"] = self.bcc_email
        message.set_content(body)
        message.add_alternative(
            render_html_email(body, self.tracking_base_url, event_id),
            subtype="html",
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        payload = {"raw": raw, "labelIds": ["DRAFT"]}

        request = Request(
            f"https://gmail.googleapis.com/gmail/v1/users/{quote(self.user_id)}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "id": data.get("id", ""),
                    "threadId": data.get("threadId", ""),
                    "provider": "gmail_draft",
                }
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Gmail draft creation failed: {exc}") from exc

    def _access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            return ""
        request = Request(
            "https://oauth2.googleapis.com/token",
            data=urlencode(
                {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.access_token = data.get("access_token", "")
                return self.access_token
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Gmail token refresh failed: {exc}") from exc


def build_email_client(settings) -> BaseEmailClient:
    provider = (settings.draft_provider or "gmail").lower()
    if provider != "gmail":
        raise RuntimeError(
            "Draft-only mode requires DRAFT_PROVIDER=gmail. "
            "Sending providers are intentionally disabled in phase one."
        )
    return GmailEmailClient(
        access_token=settings.gmail_access_token,
        from_name=settings.email_from_name,
        from_email=settings.email_from_email,
        tracking_base_url=settings.tracking_base_url,
        reply_to_email=settings.gmail_reply_to_email,
        bcc_email=settings.hubspot_bcc_email,
        refresh_token=settings.gmail_refresh_token,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        user_id=settings.gmail_user_id,
    )


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
