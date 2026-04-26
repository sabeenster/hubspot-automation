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
    gmail_from_name: str = os.getenv("GMAIL_FROM_NAME", "Sabeen")
    gmail_from_email: str = os.getenv("GMAIL_FROM_EMAIL", "sabeen@agentway.com")
    hubspot_access_token: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
    hubspot_portal_id: str = os.getenv("HUBSPOT_PORTAL_ID", "")
    gmail_access_token: str = os.getenv("GMAIL_ACCESS_TOKEN", "")
    gmail_refresh_token: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    gmail_client_id: str = os.getenv("GMAIL_CLIENT_ID", "")
    gmail_client_secret: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    google_sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    granola_api_key: str = os.getenv("GRANOLA_API_KEY", "")
    granola_api_base: str = os.getenv("GRANOLA_API_BASE", "https://api.granola.ai")
    hubspot_webhook_secret: str = os.getenv("HUBSPOT_WEBHOOK_SECRET", "")


def get_settings() -> Settings:
    return Settings()
