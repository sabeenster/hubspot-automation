import base64
import json
import uuid
from email.mime.text import MIMEText
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GmailClient:
    def __init__(self, access_token: str, from_name: str, from_email: str):
        self.access_token = access_token
        self.from_name = from_name
        self.from_email = from_email

    def send_email(self, to_email: str, subject: str, body: str, dry_run: bool = False) -> Dict[str, str]:
        if dry_run or not self.access_token:
            return {
                "id": f"dryrun-{uuid.uuid4()}",
                "threadId": f"dryrun-thread-{uuid.uuid4()}",
            }

        message = MIMEText(body)
        message["to"] = to_email
        message["from"] = f"{self.from_name} <{self.from_email}>"
        message["subject"] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        request = Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps({"raw": encoded}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Gmail send failed: {exc}") from exc

    def detect_reply(self, gmail_thread_id: str) -> bool:
        # Placeholder for Gmail thread inspection.
        return False
