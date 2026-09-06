from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


# Enums
class LeadStatus(str, PyEnum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    DEMO_CREATED = "demo_created"
    OUTREACH_QUEUED = "outreach_queued"
    EMAIL_SENT = "email_sent"
    FOLLOWUP_SENT = "followup_sent"
    CALL_SCHEDULED = "call_scheduled"
    CALL_COMPLETED = "call_completed"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CONVERTED = "converted"
    DO_NOT_CONTACT = "do_not_contact"


class OutreachType(str, PyEnum):
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    FOLLOWUP_EMAIL = "followup_email"


class OutreachStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"
    CALLED = "called"
    VOICEMAIL = "voicemail"
    ANSWERED = "answered"


# Models
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="admin")  # admin, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_place_id: Mapped[str | None] = mapped_column(String, unique=True, index=True)

    # Business info
    business_name: Mapped[str] = mapped_column(String, index=True)
    business_type: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String, index=True)
    state: Mapped[str | None] = mapped_column(String)
    zip_code: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)  # Should be None/empty for our target leads

    # Enrichment data
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    services: Mapped[str | None] = mapped_column(Text)  # JSON array of services
    hours: Mapped[str | None] = mapped_column(Text)  # JSON object
    photos: Mapped[str | None] = mapped_column(Text)  # JSON array of photo URLs
    ai_description: Mapped[str | None] = mapped_column(Text)  # LLM-generated description

    # Demo site
    demo_url: Mapped[str | None] = mapped_column(String)
    demo_template: Mapped[str | None] = mapped_column(String)
    demo_generated_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Status & scoring
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.DISCOVERED
    )
    lead_score: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    # Contact consent
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    website_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, index=True)
    outreach_type: Mapped[OutreachType] = mapped_column(Enum(OutreachType))
    status: Mapped[OutreachStatus] = mapped_column(Enum(OutreachStatus), default=OutreachStatus.PENDING)

    # Content
    subject: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    template_used: Mapped[str | None] = mapped_column(String)

    # Tracking
    message_sid: Mapped[str | None] = mapped_column(String)  # SendGrid/Twilio message ID
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Call-specific
    call_duration: Mapped[int | None] = mapped_column(Integer)  # seconds
    call_recording_url: Mapped[str | None] = mapped_column(String)
    call_transcript: Mapped[str | None] = mapped_column(Text)

    # Approval
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    target_city: Mapped[str] = mapped_column(String)
    target_state: Mapped[str] = mapped_column(String)
    target_category: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft, active, paused, completed

    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    calls_made: Mapped[int] = mapped_column(Integer, default=0)
    replies_received: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SuppressionEntry(Base):
    __tablename__ = "suppression_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # What is suppressed
    contact_type: Mapped[str] = mapped_column(String, index=True)  # email, phone, domain
    value: Mapped[str] = mapped_column(String, index=True)  # the suppressed value (lowercased for email/domain)

    # Why
    reason: Mapped[str] = mapped_column(String, index=True)  # unsubscribe, bounce, spam_report, manual, complaint
    description: Mapped[str | None] = mapped_column(Text)  # human-readable note

    # Source tracking
    source: Mapped[str | None] = mapped_column(String)  # webhook, manual, import, api
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)  # linked lead if applicable
    outreach_log_id: Mapped[int | None] = mapped_column(Integer)  # linked outreach log if applicable
    campaign_id: Mapped[int | None] = mapped_column(Integer)  # linked campaign if applicable

    # State
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    added_by: Mapped[str | None] = mapped_column(String)  # who added it (user, system, webhook)
    removed_by: Mapped[str | None] = mapped_column(String)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # SendGrid event fields
    event_type: Mapped[str] = mapped_column(String, index=True)  # delivered, open, click, bounce, etc.
    message_id: Mapped[str | None] = mapped_column(String, index=True)  # SendGrid X-Message-Id
    email: Mapped[str | None] = mapped_column(String, index=True)
    outreach_log_id: Mapped[int | None] = mapped_column(Integer, index=True)
    campaign_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # Event details
    reason: Mapped[str | None] = mapped_column(Text)  # bounce reason, etc.
    url: Mapped[str | None] = mapped_column(String)  # clicked URL
    ip_address: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)

    # Raw payload
    raw_event: Mapped[str | None] = mapped_column(Text)  # full JSON payload for debugging

    # Processing
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime)  # when the event occurred on SendGrid side
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)

    # Overall status
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, running, completed, failed, cancelled
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Configuration
    skip_discovery: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_enrichment: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_email: Mapped[bool] = mapped_column(Boolean, default=False)

    # Step 1: Discovery
    discovery_status: Mapped[str] = mapped_column(String, default="pending")  # pending, running, completed, failed, skipped
    discovery_total: Mapped[int] = mapped_column(Integer, default=0)
    discovery_new: Mapped[int] = mapped_column(Integer, default=0)
    discovery_skipped: Mapped[int] = mapped_column(Integer, default=0)
    discovery_errors: Mapped[int] = mapped_column(Integer, default=0)
    discovery_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    discovery_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    discovery_error: Mapped[str | None] = mapped_column(Text)

    # Step 2: Enrichment
    enrichment_status: Mapped[str] = mapped_column(String, default="pending")
    enrichment_total: Mapped[int] = mapped_column(Integer, default=0)
    enrichment_done: Mapped[int] = mapped_column(Integer, default=0)
    enrichment_errors: Mapped[int] = mapped_column(Integer, default=0)
    enrichment_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    enrichment_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    enrichment_error: Mapped[str | None] = mapped_column(Text)

    # Step 3: Demo generation
    demo_status: Mapped[str] = mapped_column(String, default="pending")
    demo_total: Mapped[int] = mapped_column(Integer, default=0)
    demo_done: Mapped[int] = mapped_column(Integer, default=0)
    demo_errors: Mapped[int] = mapped_column(Integer, default=0)
    demo_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    demo_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    demo_error: Mapped[str | None] = mapped_column(Text)

    # Step 4: Email outreach
    email_status: Mapped[str] = mapped_column(String, default="pending")
    email_total: Mapped[int] = mapped_column(Integer, default=0)
    email_sent: Mapped[int] = mapped_column(Integer, default=0)
    email_queued: Mapped[int] = mapped_column(Integer, default=0)
    email_suppressed: Mapped[int] = mapped_column(Integer, default=0)
    email_errors: Mapped[int] = mapped_column(Integer, default=0)
    email_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    email_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    email_error: Mapped[str | None] = mapped_column(Text)

    # Summary
    total_leads_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_emails_queued: Mapped[int] = mapped_column(Integer, default=0)
    total_emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(Text)  # JSON array of errors

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Database engine and session
import os
from urllib.parse import urlparse

_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/leadgen",
)

# Strip ALL query params from Neon's URL — asyncpg doesn't understand sslmode=
parsed = urlparse(_db_url)
_db_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?ssl=require"

print(f"[DB] Engine URL starts with: {_db_url[:60]}")

# Neon pooler authenticator needs explicit search_path for DDL
engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"server_settings": {"search_path": "public"}},
)
async_session = async_sessionmaker(engine, class_=None, expire_on_commit=False)


async def init_db():
    from sqlalchemy import text
    async with engine.begin() as conn:
        # Grant permissions for Neon pooler authenticator role
        for stmt in [
            "GRANT ALL ON SCHEMA public TO authenticator",
            "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticator",
            "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO authenticator",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO authenticator",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticator",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # role may already have these permissions
        await conn.run_sync(Base.metadata.create_all)
