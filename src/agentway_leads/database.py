import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from .models import EmailEvent, Lead, MeetingNote, Template


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL UNIQUE,
    company TEXT,
    job_title TEXT,
    source TEXT,
    source_drilldown_1 TEXT,
    source_drilldown_2 TEXT,
    utm_campaign TEXT,
    utm_ad TEXT,
    utm_content TEXT,
    ad_campaign_name TEXT,
    ad_campaign_id TEXT,
    ad_group_id TEXT,
    ad_id TEXT,
    ad_network TEXT,
    attribution_snapshot_json TEXT,
    hubspot_contact_id TEXT,
    lead_type TEXT,
    status TEXT,
    lifecycle_stage TEXT,
    last_email_sent TEXT,
    next_action_date TEXT,
    demo_booked_date TEXT,
    demo_completed INTEGER DEFAULT 0,
    notes TEXT,
    owner TEXT,
    lead_quality TEXT,
    next_step TEXT,
    confirmation_email_sent INTEGER DEFAULT 0,
    demo_confirmation_sent INTEGER DEFAULT 0,
    post_demo_followup_sent INTEGER DEFAULT 0,
    email_opt_in INTEGER DEFAULT 1,
    unsubscribed INTEGER DEFAULT 0,
    workflow_area TEXT,
    last_meeting_at TEXT,
    granola_note_url TEXT,
    granola_note_summary TEXT
);

CREATE TABLE IF NOT EXISTS email_events (
    email_event_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    email TEXT NOT NULL,
    template_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    email_provider TEXT,
    provider_message_id TEXT,
    gmail_message_id TEXT,
    gmail_thread_id TEXT,
    opened_at TEXT,
    clicked_at TEXT,
    replied_at TEXT,
    clicked_url TEXT,
    bounced INTEGER DEFAULT 0,
    unsubscribe_clicked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates (
    template_name TEXT PRIMARY KEY,
    lead_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    delay_days INTEGER DEFAULT 0,
    delay_minutes INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS meeting_notes (
    meeting_note_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    external_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    note_url TEXT,
    note_summary TEXT,
    meeting_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'granola'
);
"""

LEAD_COLUMN_MIGRATIONS = {
    "source_drilldown_1": "ALTER TABLE leads ADD COLUMN source_drilldown_1 TEXT",
    "source_drilldown_2": "ALTER TABLE leads ADD COLUMN source_drilldown_2 TEXT",
    "ad_campaign_name": "ALTER TABLE leads ADD COLUMN ad_campaign_name TEXT",
    "ad_campaign_id": "ALTER TABLE leads ADD COLUMN ad_campaign_id TEXT",
    "ad_group_id": "ALTER TABLE leads ADD COLUMN ad_group_id TEXT",
    "ad_id": "ALTER TABLE leads ADD COLUMN ad_id TEXT",
    "ad_network": "ALTER TABLE leads ADD COLUMN ad_network TEXT",
    "attribution_snapshot_json": "ALTER TABLE leads ADD COLUMN attribution_snapshot_json TEXT",
    "last_meeting_at": "ALTER TABLE leads ADD COLUMN last_meeting_at TEXT",
    "granola_note_url": "ALTER TABLE leads ADD COLUMN granola_note_url TEXT",
    "granola_note_summary": "ALTER TABLE leads ADD COLUMN granola_note_summary TEXT",
}

EMAIL_EVENT_COLUMN_MIGRATIONS = {
    "email_provider": "ALTER TABLE email_events ADD COLUMN email_provider TEXT",
    "provider_message_id": "ALTER TABLE email_events ADD COLUMN provider_message_id TEXT",
}

TEMPLATE_COLUMN_MIGRATIONS = {
    "delay_minutes": "ALTER TABLE templates ADD COLUMN delay_minutes INTEGER DEFAULT 0",
}


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate_leads_table(conn)
            self._migrate_email_events_table(conn)
            self._migrate_templates_table(conn)

    def _migrate_leads_table(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(leads)").fetchall()
        existing_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in rows
        }
        for column_name, sql in LEAD_COLUMN_MIGRATIONS.items():
            if column_name not in existing_columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise

    def _migrate_email_events_table(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(email_events)").fetchall()
        existing_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in rows
        }
        for column_name, sql in EMAIL_EVENT_COLUMN_MIGRATIONS.items():
            if column_name not in existing_columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise

    def _migrate_templates_table(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(templates)").fetchall()
        existing_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in rows
        }
        for column_name, sql in TEMPLATE_COLUMN_MIGRATIONS.items():
            if column_name not in existing_columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise

    def upsert_lead(self, lead: Lead) -> None:
        values = lead.__dict__
        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        update_clause = ", ".join(
            f"{column}=excluded.{column}" for column in values
        )
        sql = (
            f"INSERT INTO leads ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(email) DO UPDATE SET {update_clause}"
        )
        with self.connect() as conn:
            conn.execute(sql, tuple(values.values()))

    def upsert_template(self, template: Template) -> None:
        values = {
            "template_name": template.template_name,
            "lead_type": template.lead_type,
            "subject": template.subject,
            "body": template.body,
            "delay_days": template.delay_days,
            "delay_minutes": template.delay_minutes,
            "active": 1 if template.active else 0,
        }
        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        update_clause = ", ".join(
            f"{column}=excluded.{column}" for column in values if column != "template_name"
        )
        sql = (
            f"INSERT INTO templates ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(template_name) DO UPDATE SET {update_clause}"
        )
        with self.connect() as conn:
            conn.execute(sql, tuple(values.values()))

    def insert_email_event(self, event: EmailEvent) -> None:
        values = event.__dict__
        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        sql = f"INSERT INTO email_events ({columns}) VALUES ({placeholders})"
        with self.connect() as conn:
            conn.execute(sql, tuple(values.values()))

    def upsert_meeting_note(self, note: MeetingNote) -> None:
        values = note.__dict__
        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        update_clause = ", ".join(
            f"{column}=excluded.{column}" for column in values if column != "external_id"
        )
        sql = (
            f"INSERT INTO meeting_notes ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(external_id) DO UPDATE SET {update_clause}"
        )
        with self.connect() as conn:
            conn.execute(sql, tuple(values.values()))

    def update_email_event_field(self, email_event_id: str, field_name: str, value: str) -> None:
        if field_name not in {
            "opened_at",
            "clicked_at",
            "replied_at",
            "clicked_url",
            "gmail_message_id",
            "gmail_thread_id",
            "email_provider",
            "provider_message_id",
            "unsubscribe_clicked",
            "bounced",
        }:
            raise ValueError("Unsupported field update")
        with self.connect() as conn:
            conn.execute(
                f"UPDATE email_events SET {field_name} = ? WHERE email_event_id = ?",
                (value, email_event_id),
            )

    def update_lead_fields(self, lead_id: str, **fields: object) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{name} = ?" for name in fields)
        params = list(fields.values()) + [lead_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE leads SET {assignments} WHERE lead_id = ?", params)

    def get_leads(self) -> List[Lead]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
        return [Lead(**dict(row)) for row in rows]

    def get_lead_by_id(self, lead_id: str) -> Optional[Lead]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
        return Lead(**dict(row)) if row else None

    def get_templates(self) -> List[Template]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM templates WHERE active = 1").fetchall()
        return [
            Template(
                template_name=row["template_name"],
                lead_type=row["lead_type"],
                subject=row["subject"],
                body=row["body"],
                delay_days=row["delay_days"],
                delay_minutes=row["delay_minutes"],
                active=bool(row["active"]),
            )
            for row in rows
        ]

    def get_template(self, template_name: str) -> Optional[Template]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM templates WHERE template_name = ?", (template_name,)
            ).fetchone()
        if not row:
            return None
        return Template(
            template_name=row["template_name"],
            lead_type=row["lead_type"],
            subject=row["subject"],
            body=row["body"],
            delay_days=row["delay_days"],
            delay_minutes=row["delay_minutes"],
            active=bool(row["active"]),
        )

    def get_email_events(self) -> List[EmailEvent]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM email_events ORDER BY sent_at DESC"
            ).fetchall()
        return [EmailEvent(**dict(row)) for row in rows]

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM leads WHERE email = ?", (email.lower(),)).fetchone()
        return Lead(**dict(row)) if row else None

    def get_meeting_notes(self) -> List[MeetingNote]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meeting_notes ORDER BY meeting_at DESC"
            ).fetchall()
        return [MeetingNote(**dict(row)) for row in rows]
