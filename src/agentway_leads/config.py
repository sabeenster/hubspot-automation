from dataclasses import dataclass
import os


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_path: str = os.getenv("DATABASE_PATH", "./agentway_leads.db")
    base_url: str = os.getenv("BASE_URL", "https://agentway.ai")
    tracking_base_url: str = os.getenv("TRACKING_BASE_URL", "http://localhost:8080")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    email_provider: str = os.getenv("EMAIL_PROVIDER", "resend")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "Sabeen")
    email_from_email: str = os.getenv("EMAIL_FROM_EMAIL", "sabeen@agentway.com")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_from_email: str = os.getenv("RESEND_FROM_EMAIL", "")
    resend_reply_to_email: str = os.getenv("RESEND_REPLY_TO_EMAIL", "")
    hubspot_access_token: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
    hubspot_portal_id: str = os.getenv("HUBSPOT_PORTAL_ID", "")
    google_sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    granola_api_key: str = os.getenv("GRANOLA_API_KEY", "")
    granola_api_base: str = os.getenv("GRANOLA_API_BASE", "https://api.granola.ai")
    hubspot_webhook_secret: str = os.getenv("HUBSPOT_WEBHOOK_SECRET", "")


def get_settings() -> Settings:
    return Settings()
