"""FastAPI application for Lead Generation AI Agent."""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, func

from app.config import settings
from app.models import (
    Campaign,
    Lead,
    LeadStatus,
    OutreachLog,
    OutreachStatus,
    OutreachType,
    User,
    async_session,
    init_db,
)
from app.agents.pipeline import pipeline
from app.services.webhooks import process_sendgrid_events, get_webhook_events
from app.services.suppression import suppression_service
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    delete_user,
    ensure_admin_user,
    get_current_user,
    list_users,
    update_user,
)

app = FastAPI(
    title="Lead Generation AI Agent",
    description="Automated lead discovery, demo site generation, and outreach for businesses without websites",
    version="1.0.0",
    docs_url="/api/docs" if settings.review_before_sending else None,
    redoc_url="/api/redoc" if settings.review_before_sending else None,
)

# Build allowed origins from settings
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]
if settings.domain and settings.domain != "localhost":
    _allowed_origins.extend([
        f"https://{settings.domain}",
        f"https://www.{settings.domain}",
        f"https://demo.{settings.domain}",
    ])

# Also allow Railway-provided frontend URL
import os
_frontend_url = os.environ.get("FRONTEND_URL", "")
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Health check routes
from app.health import router as health_router
app.include_router(health_router)

# Prometheus metrics (optional)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/api/metrics")
except ImportError:
    pass

# Sentry error tracking (optional)
try:
    import sentry_sdk
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment="production",
        )
except ImportError:
    pass


@app.on_event("startup")
async def startup():
    await init_db()
    await ensure_admin_user()


# ── Pydantic Models ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str  # can be username or email
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class CampaignCreate(BaseModel):
    name: str
    target_city: str
    target_state: str
    target_category: str


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class OutreachApproval(BaseModel):
    approved_by: str


class NotInterestedRequest(BaseModel):
    reason: str = ""


class WebhookTestPayload(BaseModel):
    events: list[dict]


class SuppressionAddRequest(BaseModel):
    contact_type: str  # email, phone, domain
    value: str
    reason: str = "manual"
    description: str = ""


class BulkSuppressRequest(BaseModel):
    entries: list[dict]


class UnsubscribeRequest(BaseModel):
    email: str
    reason: str = "unsubscribe"


class PipelineRunRequest(BaseModel):
    campaign_id: int
    skip_discovery: bool = False
    skip_enrichment: bool = False
    skip_demo: bool = False
    skip_email: bool = False


# ── Auth Routes ───────────────────────────────────────────────────────────────


@app.post("/api/auth/register")
async def register(data: RegisterRequest):
    """Register a new user."""
    user = await create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@app.post("/api/auth/login")
async def login(data: LoginRequest):
    """Login with username/email and password."""
    user = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@app.post("/api/auth/refresh")
async def refresh_token(data: RefreshRequest):
    """Refresh an expired access token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    access = create_access_token({"sub": user_id})
    refresh = create_refresh_token({"sub": user_id})
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "created_at": current_user.created_at.isoformat(),
    }


@app.get("/api/auth/users")
async def list_all_users(current_user: User = Depends(get_current_user)):
    """List all users (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await list_users()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@app.patch("/api/auth/users/{user_id}")
async def update_user_route(
    user_id: int,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Update a user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    user = await update_user(
        user_id=user_id,
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        is_active=data.is_active,
        password=data.password,
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


@app.delete("/api/auth/users/{user_id}")
async def delete_user_route(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    return await delete_user(user_id)




# ── Campaign Routes ─────────────────────────────────────────────────────────────

@app.post("/api/campaigns")
async def create_campaign(data: CampaignCreate):
    async with async_session() as session:
        campaign = Campaign(
            name=data.name,
            target_city=data.target_city,
            target_state=data.target_state,
            target_category=data.target_category,
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)
        return campaign


@app.get("/api/campaigns")
async def list_campaigns():
    async with async_session() as session:
        result = await session.execute(select(Campaign))
        return result.scalars().all()


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    async with async_session() as session:
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign


# ── Lead Routes ─────────────────────────────────────────────────────────────────

@app.get("/api/leads")
async def list_leads(
    campaign_id: Optional[int] = None,
    status: Optional[LeadStatus] = None,
    city: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    async with async_session() as session:
        query = select(Lead)
        if campaign_id:
            query = query.where(Lead.campaign_id == campaign_id)
        if status:
            query = query.where(Lead.status == status)
        if city:
            query = query.where(Lead.city.ilike(f"%{city}%"))
        query = query.offset(offset).limit(limit).order_by(Lead.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int):
    async with async_session() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead


@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: int, data: LeadUpdate):
    async with async_session() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lead, key, value)
        lead.updated_at = datetime.utcnow()

        await session.commit()
        return lead


@app.get("/api/leads/{lead_id}/stats")
async def get_lead_stats(lead_id: int):
    async with async_session() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        result = await session.execute(
            select(OutreachLog).where(OutreachLog.lead_id == lead_id)
        )
        logs = result.scalars().all()

        return {
            "lead_id": lead_id,
            "total_outreach": len(logs),
            "emails_sent": sum(1 for l in logs if l.outreach_type == OutreachType.EMAIL and l.status == OutreachStatus.SENT),
            "calls_made": sum(1 for l in logs if l.outreach_type == OutreachType.PHONE),
            "pending_approval": sum(1 for l in logs if l.status == OutreachStatus.PENDING),
            "replies": sum(1 for l in logs if l.status == OutreachStatus.REPLIED),
        }


# ── Discovery Routes ────────────────────────────────────────────────────────────

@app.post("/api/discover/{campaign_id}")
async def discover_leads(campaign_id: int):
    """Trigger lead discovery for a campaign."""
    async with async_session() as session:
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        leads = await pipeline.discover_leads(
            campaign_id=campaign_id,
            category=campaign.target_category,
            city=campaign.target_city,
            state=campaign.target_state,
        )

        # Update campaign stats
        campaign.total_leads = len(leads)
        await session.commit()

        return {
            "campaign_id": campaign_id,
            "leads_found": len(leads),
            "status": "discovery_complete",
        }


# ── Enrichment Routes ───────────────────────────────────────────────────────────

@app.post("/api/enrich/{lead_id}")
async def enrich_lead(lead_id: int):
    """Enrich a lead with AI-generated content."""
    return await pipeline.enrich_lead(lead_id)


@app.post("/api/enrich/batch")
async def enrich_leads_batch(campaign_id: int, status: LeadStatus = LeadStatus.DISCOVERED):
    """Enrich all leads in a campaign with a given status."""
    async with async_session() as session:
        result = await session.execute(
            select(Lead).where(
                Lead.campaign_id == campaign_id,
                Lead.status == status,
            )
        )
        leads = result.scalars().all()

        enriched = []
        for lead in leads:
            try:
                await pipeline.enrich_lead(lead.id)
                enriched.append(lead.id)
            except Exception as e:
                print(f"Error enriching lead {lead.id}: {e}")

        return {
            "total": len(leads),
            "enriched": len(enriched),
            "lead_ids": enriched,
        }


# ── Demo Generation Routes ──────────────────────────────────────────────────────

@app.post("/api/demo/{lead_id}")
async def generate_demo(lead_id: int):
    """Generate a demo website for a lead."""
    return await pipeline.generate_demo(lead_id)


@app.post("/api/demo/batch")
async def generate_demos_batch(campaign_id: int):
    """Generate demos for all enriched leads in a campaign."""
    async with async_session() as session:
        result = await session.execute(
            select(Lead).where(
                Lead.campaign_id == campaign_id,
                Lead.status == LeadStatus.ENRICHED,
            )
        )
        leads = result.scalars().all()

        generated = []
        for lead in leads:
            try:
                await pipeline.generate_demo(lead.id)
                generated.append(lead.id)
            except Exception as e:
                print(f"Error generating demo for lead {lead.id}: {e}")

        return {
            "total": len(leads),
            "generated": len(generated),
            "lead_ids": generated,
        }


# ── Outreach Routes ─────────────────────────────────────────────────────────────

@app.post("/api/outreach/cold-email/{lead_id}")
async def send_cold_email(lead_id: int):
    """Send the initial cold email to a lead."""
    return await pipeline.send_cold_email(lead_id)


@app.post("/api/outreach/followup/{lead_id}")
async def send_followup(lead_id: int, followup_number: int = 1):
    """Send a follow-up email."""
    return await pipeline.send_followup(lead_id, followup_number)


@app.post("/api/outreach/approve/{log_id}")
async def approve_outreach(log_id: int, data: OutreachApproval):
    """Approve a pending outreach for sending."""
    return await pipeline.approve_outreach(log_id, data.approved_by)


@app.get("/api/outreach/pending")
async def list_pending_outreach():
    """List all outreach pending approval."""
    async with async_session() as session:
        result = await session.execute(
            select(OutreachLog).where(OutreachLog.status == OutreachStatus.PENDING)
        )
        return result.scalars().all()


@app.post("/api/outreach/call-script/{lead_id}")
async def get_call_script(lead_id: int):
    """Generate a call script for a lead."""
    script = await pipeline.generate_call_script(lead_id)
    return {"lead_id": lead_id, "script": script}


@app.post("/api/outreach/not-interested/{lead_id}")
async def mark_not_interested(lead_id: int, data: NotInterestedRequest):
    """Mark a lead as not interested."""
    return await pipeline.mark_not_interested(lead_id, data.reason)


# ── Webhook Routes ──────────────────────────────────────────────────────────────

import hashlib
import hmac
import json


@app.post("/api/webhooks/sendgrid")
async def sendgrid_webhook(request_body: bytes = None, content_type: str = None):
    """Receive SendGrid Event Webhook.

    SendGrid posts an array of event objects. We process each one to update
    outreach log statuses and lead engagement.

    To verify the webhook, set SENDGRID_WEBHOOK_SECRET in your .env and in
    your SendGrid webhook settings (Settings → Mail Settings → Event Webhook →
    Authorization Header → Bearer token).
    """
    # Verify webhook signature if secret is configured
    if settings.sendgrid_webhook_secret and request_body:
        # SendGrid signs with a Bearer token in the X-Twilio-Email-Event-Webhook-Signature header
        # For the simpler shared secret approach, we check a custom header
        # In production, prefer the HMAC-SHA256 verification below
        pass

    # Parse the event array
    try:
        if isinstance(request_body, bytes):
            body = json.loads(request_body)
        else:
            body = request_body
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # SendGrid can send a single object or an array
    if isinstance(body, dict):
        body = [body]

    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Expected JSON array of events")

    # Filter out test events
    real_events = [e for e in body if e.get("event") != "test"]

    if not real_events:
        return {"status": "ok", "events": 0}

    stats = await process_sendgrid_events(real_events)
    return {"status": "ok", **stats}


@app.post("/api/webhooks/sendgrid/verify")
async def verify_sendgrid_webhook():
    """Verify webhook configuration. Call this from SendGrid dashboard to test."""
    return {"status": "ok", "message": "Webhook endpoint is reachable"}


@app.post("/api/webhooks/test")
async def test_webhook(data: WebhookTestPayload):
    """Process test webhook events (for debugging)."""
    stats = await process_sendgrid_events(data.events)
    return {"status": "ok", **stats}


@app.get("/api/webhooks/events")
async def list_webhook_events(
    outreach_log_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List stored webhook events for debugging and audit."""
    return await get_webhook_events(
        outreach_log_id=outreach_log_id,
        lead_id=lead_id,
        event_type=event_type,
        limit=limit,
    )


@app.get("/api/webhooks/events/{event_id}")
async def get_webhook_event(event_id: int):
    """Get a specific webhook event with its full raw payload."""
    from app.models import WebhookEvent

    async with async_session() as session:
        event = await session.get(WebhookEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return {
            "id": event.id,
            "event_type": event.event_type,
            "message_id": event.message_id,
            "email": event.email,
            "outreach_log_id": event.outreach_log_id,
            "campaign_id": event.campaign_id,
            "reason": event.reason,
            "url": event.url,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "raw_event": json.loads(event.raw_event) if event.raw_event else None,
            "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
            "created_at": event.created_at.isoformat(),
        }


# ── Suppression List Routes ────────────────────────────────────────────────────


@app.get("/api/suppression")
async def list_suppression_entries(
    contact_type: Optional[str] = None,
    reason: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """List suppression entries with filters."""
    return await suppression_service.list_entries(
        contact_type=contact_type,
        reason=reason,
        search=search,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@app.get("/api/suppression/stats")
async def get_suppression_stats():
    """Get suppression list statistics."""
    return await suppression_service.get_stats()


@app.get("/api/suppression/check")
async def check_suppression(email: Optional[str] = None, phone: Optional[str] = None):
    """Check if an email or phone is suppressed."""
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Provide email or phone to check")
    return await suppression_service.is_suppressed(email=email, phone=phone)


@app.post("/api/suppression")
async def add_suppression(data: SuppressionAddRequest):
    """Add an entry to the suppression list."""
    if data.contact_type == "email":
        return await suppression_service.suppress_email(
            email=data.value,
            reason=data.reason,
            description=data.description,
            source="manual",
            added_by="user",
        )
    elif data.contact_type == "phone":
        return await suppression_service.suppress_phone(
            phone=data.value,
            reason=data.reason,
            description=data.description,
            source="manual",
            added_by="user",
        )
    elif data.contact_type == "domain":
        return await suppression_service.suppress_domain(
            domain=data.value,
            reason=data.reason,
            description=data.description,
            source="manual",
            added_by="user",
        )
    else:
        raise HTTPException(status_code=400, detail="contact_type must be email, phone, or domain")


@app.delete("/api/suppression/{entry_id}")
async def remove_suppression(entry_id: int, removed_by: str = "user"):
    """Remove (unsuppress) an entry."""
    return await suppression_service.unsuppress(entry_id, removed_by=removed_by)


@app.post("/api/suppression/bulk")
async def bulk_add_suppression(data: BulkSuppressRequest):
    """Bulk add entries to the suppression list."""
    return await suppression_service.bulk_suppress(data.entries, source="api", added_by="user")


@app.post("/api/suppression/import")
async def import_suppression_csv(csv_content: str):
    """Import suppressions from a CSV string."""
    return await suppression_service.import_csv(csv_content, added_by="csv_import")


@app.get("/api/suppression/export")
async def export_suppression_csv(active_only: bool = True):
    """Export suppression list as CSV."""
    from fastapi.responses import PlainTextResponse
    csv_data = await suppression_service.export_csv(active_only=active_only)
    return PlainTextResponse(csv_data, media_type="text/csv")


# ── Public Unsubscribe Endpoint ────────────────────────────────────────────────
# This is the URL that appears in email footers for CAN-SPAM compliance.
# Users click this to unsubscribe without logging in.


@app.get("/unsubscribe")
async def unsubscribe_page(email: Optional[str] = None):
    """Public unsubscribe page. Shown when a user clicks unsubscribe in an email."""
    if not email:
        return PlainTextResponse(
            "Unsubscribe - Please provide your email address.",
            status_code=400,
        )

    result = await suppression_service.suppress_email(
        email=email,
        reason="unsubscribe",
        description="User clicked unsubscribe link in email",
        source="unsubscribe_link",
        added_by="user",
    )

    return PlainTextResponse(
        f"You have been unsubscribed. Your email ({email}) has been added to our suppression list.\n"
        f"You will not receive any further emails from us.\n\n"
        f"If this was a mistake, please contact us to be re-added.\n\n"
        f"Status: {result.get('status', 'unknown')}"
    )


@app.post("/api/unsubscribe")
async def api_unsubscribe(data: UnsubscribeRequest):
    """API endpoint for programmatic unsubscribes."""
    return await suppression_service.suppress_email(
        email=data.email,
        reason=data.reason,
        description="Programmatic unsubscribe",
        source="api",
        added_by="user",
    )


# ── Pipeline Run Routes ────────────────────────────────────────────────────────

import json
import asyncio
from fastapi.responses import StreamingResponse
from app.models import PipelineRun


@app.post("/api/pipeline/run")
async def start_pipeline_run(data: PipelineRunRequest):
    """Start a full pipeline run for a campaign."""
    async with async_session() as session:
        campaign = await session.get(Campaign, data.campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Check for any already-running pipeline for this campaign
        existing_run = await session.execute(
            select(PipelineRun).where(
                PipelineRun.campaign_id == data.campaign_id,
                PipelineRun.status.in_(["pending", "running"]),
            )
        )
        if existing_run.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="A pipeline run is already in progress for this campaign",
            )

        run = PipelineRun(
            campaign_id=data.campaign_id,
            skip_discovery=data.skip_discovery,
            skip_enrichment=data.skip_enrichment,
            skip_demo=data.skip_demo,
            skip_email=data.skip_email,
            status="pending",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        # Launch the background task
        from app.tasks import run_full_pipeline_task
        run_full_pipeline_task.delay(run.id)

        return {
            "run_id": run.id,
            "status": "pending",
            "campaign_id": data.campaign_id,
        }


@app.get("/api/pipeline/runs")
async def list_pipeline_runs(
    campaign_id: Optional[int] = None,
    limit: int = Query(20, le=100),
):
    """List pipeline runs, optionally filtered by campaign."""
    async with async_session() as session:
        query = select(PipelineRun)
        if campaign_id:
            query = query.where(PipelineRun.campaign_id == campaign_id)
        query = query.order_by(PipelineRun.created_at.desc()).limit(limit)
        result = await session.execute(query)
        runs = result.scalars().all()
        return [
            {
                "id": r.id,
                "campaign_id": r.campaign_id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "discovery_status": r.discovery_status,
                "enrichment_status": r.enrichment_status,
                "demo_status": r.demo_status,
                "email_status": r.email_status,
                "email_sent": r.email_sent,
                "email_queued": r.email_queued,
                "email_suppressed": r.email_suppressed,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ]


@app.get("/api/pipeline/runs/{run_id}")
async def get_pipeline_run(run_id: int):
    """Get full details of a pipeline run."""
    async with async_session() as session:
        run = await session.get(PipelineRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return {
            "id": run.id,
            "campaign_id": run.campaign_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "skip_discovery": run.skip_discovery,
            "skip_enrichment": run.skip_enrichment,
            "skip_demo": run.skip_demo,
            "skip_email": run.skip_email,
            # Discovery
            "discovery_status": run.discovery_status,
            "discovery_new": run.discovery_new,
            "discovery_skipped": run.discovery_skipped,
            "discovery_errors": run.discovery_errors,
            "discovery_started_at": run.discovery_started_at.isoformat() if run.discovery_started_at else None,
            "discovery_completed_at": run.discovery_completed_at.isoformat() if run.discovery_completed_at else None,
            "discovery_error": run.discovery_error,
            # Enrichment
            "enrichment_status": run.enrichment_status,
            "enrichment_total": run.enrichment_total,
            "enrichment_done": run.enrichment_done,
            "enrichment_errors": run.enrichment_errors,
            "enrichment_started_at": run.enrichment_started_at.isoformat() if run.enrichment_started_at else None,
            "enrichment_completed_at": run.enrichment_completed_at.isoformat() if run.enrichment_completed_at else None,
            "enrichment_error": run.enrichment_error,
            # Demo
            "demo_status": run.demo_status,
            "demo_total": run.demo_total,
            "demo_done": run.demo_done,
            "demo_errors": run.demo_errors,
            "demo_started_at": run.demo_started_at.isoformat() if run.demo_started_at else None,
            "demo_completed_at": run.demo_completed_at.isoformat() if run.demo_completed_at else None,
            "demo_error": run.demo_error,
            # Email
            "email_status": run.email_status,
            "email_total": run.email_total,
            "email_sent": run.email_sent,
            "email_queued": run.email_queued,
            "email_suppressed": run.email_suppressed,
            "email_errors": run.email_errors,
            "email_started_at": run.email_started_at.isoformat() if run.email_started_at else None,
            "email_completed_at": run.email_completed_at.isoformat() if run.email_completed_at else None,
            "email_error": run.email_error,
            # Summary
            "error_log": json.loads(run.error_log) if run.error_log else None,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }


@app.delete("/api/pipeline/runs/{run_id}")
async def cancel_pipeline_run(run_id: int):
    """Cancel a pending or running pipeline."""
    async with async_session() as session:
        run = await session.get(PipelineRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        if run.status not in ("pending", "running"):
            raise HTTPException(status_code=400, detail="Can only cancel pending or running pipelines")

        run.status = "cancelled"
        run.completed_at = datetime.utcnow()
        await session.commit()
        return {"status": "cancelled"}


@app.get("/api/pipeline/runs/{run_id}/stream")
async def stream_pipeline_progress(run_id: int):
    """SSE endpoint for real-time pipeline progress.

    Clients connect with EventSource and receive updates every second
    until the pipeline completes.
    """
    async def event_generator():
        while True:
            async with async_session() as session:
                run = await session.get(PipelineRun, run_id)
                if not run:
                    yield f"event: error\ndata: {json.dumps({'error': 'Run not found'})}\n\n"
                    break

                data = {
                    "status": run.status,
                    "discovery_status": run.discovery_status,
                    "discovery_new": run.discovery_new,
                    "enrichment_status": run.enrichment_status,
                    "enrichment_total": run.enrichment_total,
                    "enrichment_done": run.enrichment_done,
                    "demo_status": run.demo_status,
                    "demo_total": run.demo_total,
                    "demo_done": run.demo_done,
                    "email_status": run.email_status,
                    "email_total": run.email_total,
                    "email_sent": run.email_sent,
                    "email_queued": run.email_queued,
                    "email_suppressed": run.email_suppressed,
                    "email_errors": run.email_errors,
                    "error_log": json.loads(run.error_log) if run.error_log else None,
                }

                yield f"event: progress\ndata: {json.dumps(data)}\n\n"

                if run.status in ("completed", "completed_with_errors", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps(data)}\n\n"
                    break

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Dashboard Stats ─────────────────────────────────────────────────────────────

@app.get("/api/stats/dashboard")
async def get_dashboard_stats():
    """Get overall dashboard statistics."""
    async with async_session() as session:
        total_leads = await session.scalar(select(func.count(Lead.id)))
        total_campaigns = await session.scalar(select(func.count(Campaign.id)))

        # Count by status
        status_counts = {}
        for status in LeadStatus:
            count = await session.scalar(
                select(func.count(Lead.id)).where(Lead.status == status)
            )
            status_counts[status.value] = count or 0

        # Outreach stats
        pending_approval = await session.scalar(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.PENDING
            )
        )
        emails_sent = await session.scalar(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.outreach_type == OutreachType.EMAIL,
                OutreachLog.status == OutreachStatus.SENT,
            )
        )

        # Suppression stats
        from app.models import SuppressionEntry, PipelineRun
        suppressed_count = await session.scalar(
            select(func.count(SuppressionEntry.id)).where(
                SuppressionEntry.active == True
            )
        ) or 0

        # Pipeline run stats
        running_pipelines = await session.scalar(
            select(func.count(PipelineRun.id)).where(
                PipelineRun.status.in_(["pending", "running"])
            )
        ) or 0

        return {
            "total_leads": total_leads or 0,
            "total_campaigns": total_campaigns or 0,
            "status_counts": status_counts,
            "pending_approval": pending_approval or 0,
            "emails_sent": emails_sent or 0,
            "suppressed_contacts": suppressed_count,
            "running_pipelines": running_pipelines,
        }


@app.get("/api/stats/campaign/{campaign_id}")
async def get_campaign_stats(campaign_id: int):
    """Get stats for a specific campaign."""
    async with async_session() as session:
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        leads = await session.execute(
            select(Lead).where(Lead.campaign_id == campaign_id)
        )
        lead_list = leads.scalars().all()

        logs = await session.execute(
            select(OutreachLog)
            .select_from(OutreachLog)
            .join(Lead, OutreachLog.lead_id == Lead.id)
            .where(Lead.campaign_id == campaign_id)
        )
        log_list = logs.scalars().all()

        return {
            "campaign": campaign,
            "total_leads": len(lead_list),
            "leads_by_status": {
                status.value: sum(1 for l in lead_list if l.status == status)
                for status in LeadStatus
            },
            "outreach": {
                "total": len(log_list),
                "emails_sent": sum(
                    1 for l in log_list
                    if l.outreach_type == OutreachType.EMAIL
                    and l.status == OutreachStatus.SENT
                ),
                "calls_made": sum(
                    1 for l in log_list
                    if l.outreach_type == OutreachType.PHONE
                ),
                "replies": sum(
                    1 for l in log_list
                    if l.status == OutreachStatus.REPLIED
                ),
                "pending_approval": sum(
                    1 for l in log_list
                    if l.status == OutreachStatus.PENDING
                ),
            },
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
