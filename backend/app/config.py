from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/leadgen"
    redis_url: str = "redis://localhost:6379/0"

    # Google Places API
    google_places_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # SendGrid
    sendgrid_api_key: str = ""
    sendgrid_webhook_secret: str = ""
    email_from_address: str = ""
    email_from_name: str = ""
    unsubscribe_url: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Domain
    domain: str = "localhost"

    # Demo site hosting
    demo_base_url: str = "https://demo.yourdomain.com"

    # App settings
    review_before_sending: bool = True
    max_emails_per_day: int = 50
    max_calls_per_day: int = 20

    # Security
    secret_key: str = "change-me-in-production"

    # Monitoring
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
