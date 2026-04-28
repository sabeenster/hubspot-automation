import argparse
import json
from pathlib import Path

from .automation import determine_automations, queue_approval_requests
from .config import get_settings
from .database import Database
from .email_sender import build_email_client
from .granola import GranolaClient, sync_granola_notes
from .hubspot import HubSpotClient, contact_to_lead
from .reporting import generate_weekly_report
from .sheets import GoogleSheetsSync
from .slack import SlackNotifier
from .tracking_server import serve_tracking


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentway lead automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser("seed-templates")

    sync_parser = subparsers.add_parser("sync-hubspot")
    sync_parser.add_argument("--sample-data", help="Path to sample HubSpot JSON")
    sync_parser.add_argument("--limit", type=int, default=100)

    granola_parser = subparsers.add_parser("sync-granola")
    granola_parser.add_argument("--sample-data", help="Path to sample Granola JSON")

    automation_parser = subparsers.add_parser("run-automations")
    automation_parser.add_argument("--dry-run", action="store_true")

    sync_all_parser = subparsers.add_parser("sync-all")
    sync_all_parser.add_argument("--dry-run", action="store_true")
    sync_all_parser.add_argument("--hubspot-sample-data", help="Path to sample HubSpot JSON")
    sync_all_parser.add_argument("--granola-sample-data", help="Path to sample Granola JSON")
    sync_all_parser.add_argument("--skip-sheets", action="store_true")

    subparsers.add_parser("weekly-report")

    track_parser = subparsers.add_parser("serve-tracking")
    track_parser.add_argument("--host")
    track_parser.add_argument("--port", type=int)

    subparsers.add_parser("sync-sheets")
    return parser


def main() -> None:
    settings = get_settings()
    db = Database(settings.database_path)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        db.init_db()
        print(f"Initialized database at {settings.database_path}")
        return

    if args.command == "seed-templates":
        db.init_db()
        seed_path = Path("templates/seed_templates.json")
        templates = json.loads(seed_path.read_text())
        for template in templates:
            from .models import Template

            db.upsert_template(Template(**template))
        print(f"Seeded {len(templates)} templates")
        return

    if args.command == "sync-hubspot":
        db.init_db()
        client = HubSpotClient(settings.hubspot_access_token)
        contacts = (
            client.load_sample_contacts(args.sample_data)
            if args.sample_data
            else client.fetch_recent_contacts(limit=args.limit)
        )
        leads = [contact_to_lead(contact) for contact in contacts if contact.get("properties", {}).get("email")]
        for lead in leads:
            db.upsert_lead(lead)
        decisions = determine_automations(db.get_leads())
        queued = queue_approval_requests(
            db,
            decisions,
            SlackNotifier(settings.slack_webhook_url, settings.base_url, settings.admin_token),
        )
        print(f"Synced {len(leads)} leads and queued {len(queued)} approval requests")
        return

    if args.command == "run-automations":
        db.init_db()
        decisions = determine_automations(db.get_leads())
        queued = queue_approval_requests(
            db,
            decisions,
            SlackNotifier(settings.slack_webhook_url, settings.base_url, settings.admin_token),
        )
        print(f"Evaluated {len(decisions)} automations and queued {len(queued)} approval requests")
        return

    if args.command == "sync-all":
        db.init_db()

        hubspot_client = HubSpotClient(settings.hubspot_access_token)
        contacts = (
            hubspot_client.load_sample_contacts(args.hubspot_sample_data)
            if args.hubspot_sample_data
            else hubspot_client.fetch_recent_contacts(limit=100)
        )
        leads = [
            contact_to_lead(contact)
            for contact in contacts
            if contact.get("properties", {}).get("email")
        ]
        for lead in leads:
            db.upsert_lead(lead)

        granola_client = GranolaClient(settings.granola_api_key, settings.granola_api_base)
        notes = (
            granola_client.load_sample_notes(args.granola_sample_data)
            if args.granola_sample_data
            else granola_client.fetch_notes()
        )
        linked = sync_granola_notes(db, notes)

        decisions = determine_automations(db.get_leads())
        queued = queue_approval_requests(
            db,
            decisions,
            SlackNotifier(settings.slack_webhook_url, settings.base_url, settings.admin_token),
        )

        if not args.skip_sheets:
            sync = GoogleSheetsSync(
                sheet_id=settings.google_sheet_id,
                service_account_json=settings.google_service_account_json,
                apps_script_webhook_url=settings.sheets_apps_script_url,
            )
            sync.push_leads(db.get_leads())
            sync.push_email_events(db.get_email_events())
            sync.push_meeting_notes(db.get_meeting_notes())

        print(
            "Sync complete: "
            f"{len(leads)} leads, {linked} meeting notes, {len(decisions)} automations, {len(queued)} approvals queued"
        )
        return

    if args.command == "weekly-report":
        db.init_db()
        report = generate_weekly_report(db)
        print(json.dumps(report, indent=2, default=str))
        return

    if args.command == "serve-tracking":
        db.init_db()
        email_client = build_email_client(settings)
        serve_tracking(
            db,
            settings.base_url,
            settings.hubspot_webhook_secret,
            email_client,
            HubSpotClient(settings.hubspot_access_token),
            SlackNotifier(settings.slack_webhook_url, settings.base_url, settings.admin_token),
            settings.admin_token,
            settings.automatic_email_enabled,
            host=args.host or settings.host,
            port=args.port or settings.port,
        )
        return

    if args.command == "sync-sheets":
        db.init_db()
        sync = GoogleSheetsSync(
            sheet_id=settings.google_sheet_id,
            service_account_json=settings.google_service_account_json,
            apps_script_webhook_url=settings.sheets_apps_script_url,
        )
        sync.push_leads(db.get_leads())
        sync.push_email_events(db.get_email_events())
        sync.push_meeting_notes(db.get_meeting_notes())
        print("Synced leads, email events, and meeting notes to Google Sheets")
        return

    if args.command == "sync-granola":
        db.init_db()
        client = GranolaClient(settings.granola_api_key, settings.granola_api_base)
        notes = client.load_sample_notes(args.sample_data) if args.sample_data else client.fetch_notes()
        linked = sync_granola_notes(db, notes)
        print(f"Linked {linked} Granola meeting notes")
        return


if __name__ == "__main__":
    main()
