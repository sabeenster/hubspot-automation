import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import ApprovalRequest, Lead, Template


class SlackNotifier:
    def __init__(self, webhook_url: str, base_url: str, admin_token: str = ""):
        self.webhook_url = webhook_url
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token

    def send_approval_request(
        self,
        approval_request: ApprovalRequest,
        lead: Lead,
        template: Template,
    ) -> bool:
        if not self.webhook_url:
            return False

        approve_url = (
            f"{self.base_url}/approve-email?"
            f"approval_request_id={approval_request.approval_request_id}"
            f"&approval_token={approval_request.approval_token}"
        )
        admin_url = f"{self.base_url}/admin"
        if self.admin_token:
            admin_url += f"?admin_token={self.admin_token}"
        title = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email
        payload = {
            "text": f"Approval needed to send {template.template_name} to {lead.email}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Approval needed: lead email"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Lead*\n{title}"},
                        {"type": "mrkdwn", "text": f"*Email*\n{lead.email}"},
                        {"type": "mrkdwn", "text": f"*Template*\n{template.template_name}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Source*\n{lead.source or 'unknown'} / {lead.ad_activity or lead.ad_campaign_name or 'n/a'}",
                        },
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve + Send"},
                            "style": "primary",
                            "url": approve_url,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Open Admin"},
                            "url": admin_url,
                        },
                    ],
                },
            ],
        }
        request = Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30):
                return True
        except (HTTPError, URLError):
            return False
