from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request

from .admin_ui import render_admin_page
from .automation import send_confirmation_for_lead
from .database import Database
from .email_sender import ResendEmailClient
from .models import utcnow_iso
from .webhooks import ingest_hubspot_webhook, verify_hubspot_signature


PIXEL_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


class TrackingHandler(BaseHTTPRequestHandler):
    db: Database = None  # type: ignore[assignment]
    base_url: str = ""
    hubspot_webhook_secret: str = ""
    email_client: ResendEmailClient = None  # type: ignore[assignment]
    admin_token: str = ""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        event_id = query.get("event_id", [""])[0]

        if parsed.path in {"/", "/healthz"}:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            return

        if parsed.path == "/admin":
            if not self.is_authorized(query):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Admin token required")
                return
            flash_message = query.get("message", [""])[0]
            page = render_admin_page(
                self.db.get_leads(),
                self.db.get_templates(),
                flash_message=flash_message,
                admin_token=self.current_admin_token(query),
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
            return

        if parsed.path == "/email/open" and event_id:
            self.db.update_email_event_field(event_id, "opened_at", utcnow_iso())
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(PIXEL_BYTES)))
            self.end_headers()
            self.wfile.write(PIXEL_BYTES)
            return

        if parsed.path == "/r" and event_id:
            target = query.get("url", [self.base_url])[0]
            self.db.update_email_event_field(event_id, "clicked_at", utcnow_iso())
            self.db.update_email_event_field(event_id, "clicked_url", target)
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        if parsed.path == "/webhooks/hubspot":
            signature = self.headers.get("X-HubSpot-Signature-256", "")
            if not verify_hubspot_signature(body, signature, self.hubspot_webhook_secret):
                self.send_response(401)
                self.end_headers()
                return
            ingested = ingest_hubspot_webhook(self.db, body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ingested": ingested}).encode("utf-8"))
            return

        form = parse_qs(body.decode("utf-8"))

        if parsed.path == "/admin/templates":
            if not self.is_authorized(form):
                self.send_response(403)
                self.end_headers()
                return
            template_name = form.get("template_name", [""])[0]
            delay_days = int(form.get("delay_days", ["0"])[0] or "0")
            delay_minutes = int(form.get("delay_minutes", ["0"])[0] or "0")
            self.db.update_template_delay(template_name, delay_days, delay_minutes)
            self.redirect_admin("Delay updated", form)
            return

        if parsed.path == "/admin/send-confirmation":
            if not self.is_authorized(form):
                self.send_response(403)
                self.end_headers()
                return
            lead_id = form.get("lead_id", [""])[0]
            try:
                event = send_confirmation_for_lead(self.db, self.email_client, lead_id)
                self.redirect_admin(f"Confirmation sent: {event.template_name}", form)
            except ValueError as exc:
                self.redirect_admin(str(exc), form)
            return

        self.send_response(404)
        self.end_headers()

    def is_authorized(self, params) -> bool:
        if not self.admin_token:
            return True
        return self.current_admin_token(params) == self.admin_token

    def current_admin_token(self, params) -> str:
        return params.get("admin_token", [""])[0]

    def redirect_admin(self, message: str, params) -> None:
        query = {"message": message}
        token = self.current_admin_token(params)
        if token:
            query["admin_token"] = token
        self.send_response(303)
        self.send_header("Location", "/admin?" + urlencode(query))
        self.end_headers()


def serve_tracking(
    db: Database,
    base_url: str,
    hubspot_webhook_secret: str,
    email_client: ResendEmailClient,
    admin_token: str = "",
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    handler = type(
        "BoundTrackingHandler",
        (TrackingHandler,),
        {
            "db": db,
            "base_url": base_url,
            "hubspot_webhook_secret": hubspot_webhook_secret,
            "email_client": email_client,
            "admin_token": admin_token,
        },
    )
    server = HTTPServer((host, port), handler)
    print(f"Tracking server listening on http://{host}:{port}")
    server.serve_forever()
