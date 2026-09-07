"""SendGrid webhook event processing.

SendGrid posts event arrays to your webhook URL. Each event is a dict with fields like:
  event, email, sg_message_id, timestamp, url, reason, status, ip, useragent, etc.

We look up the OutreachLog by sg_message_id (stored as message_sid) or by custom args
(outreach_log_id, campaign_id) and update the log + lead status accordingly.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models import (
    Lead,
    LeadStatus,
    OutreachLog,
    OutreachStatus,
    WebhookEvent,
    async_session,
)
from app.services.suppression import suppression_service

# SendGrid event types we care about
TRACKABLE_EVENTS = {
    "delivered",
    "open",
    "click",
    "bounce",
    "dropped",
    "spamreport",
    "unsubscribe",
    "deferred",
    "processed",
    "deferred",
}

# Map SendGrid event → our OutreachStatus
EVENT_TO_STATUS = {
    "delivered": OutreachStatus.DELIVERED,
    "open": OutreachStatus.OPENED,
    "click": OutreachStatus.CLICKED,
    "bounce": OutreachStatus.BOUNCED,
    "dropped": OutreachStatus.FAILED,
    "spamreport": OutreachStatus.FAILED,
    "unsubscribe": OutreachStatus.FAILED,
    "deferred": OutreachStatus.SENT,  # still trying
    "processed": OutreachStatus.SENT,
}

# Lead status updates based on outreach engagement
ENGAGEMENT_LEAD_STATUS = {
    "open": None,  # don't change lead status on open alone
    "click": None,  # don't change on click alone
    "bounce": LeadStatus.DO_NOT_CONTACT,
    "spamreport": LeadStatus.DO_NOT_CONTACT,
    "unsubscribe": LeadStatus.DO_NOT_CONTACT,
}


async def process_sendgrid_events(events: list[dict]) -> dict:
    """Process a batch of SendGrid webhook events.

    Returns a summary of what was processed.
    """
    stats = {"total": len(events), "processed": 0, "skipped": 0, "errors": 0}

    async with async_session() as session:
        for event in events:
            try:
                await _process_single_event(session, event)
                stats["processed"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"Error processing webhook event: {e}")

        await session.commit()

    return stats


async def _process_single_event(session, event: dict):
    """Process a single SendGrid event and update our records."""
    event_type = event.get("event", "")
    sg_message_id = event.get("sg_message_id", "")
    email = event.get("email", "")
    timestamp_unix = event.get("timestamp")

    # Parse timestamp
    event_timestamp = None
    if timestamp_unix:
        try:
            event_timestamp = datetime.utcfromtimestamp(int(timestamp_unix))
        except (ValueError, TypeError):
            pass

    # Extract custom args (we pass outreach_log_id and campaign_id)
    custom_args = event.get("custom_args", {})
    if isinstance(custom_args, str):
        try:
            custom_args = json.loads(custom_args)
        except json.JSONDecodeError:
            custom_args = {}

    outreach_log_id = custom_args.get("outreach_log_id")
    campaign_id = custom_args.get("campaign_id")

    # Store raw event
    webhook_event = WebhookEvent(
        event_type=event_type,
        message_id=sg_message_id,
        email=email,
        outreach_log_id=int(outreach_log_id) if outreach_log_id else None,
        campaign_id=int(campaign_id) if campaign_id else None,
        reason=event.get("reason"),
        url=event.get("url"),
        ip_address=event.get("ip"),
        user_agent=event.get("useragent"),
        raw_event=json.dumps(event),
        event_timestamp=event_timestamp,
        processed=True,
        processed_at=datetime.utcnow(),
    )
    session.add(webhook_event)

    # Skip non-trackable events
    if event_type not in TRACKABLE_EVENTS:
        return

    # Find the outreach log by message_sid or by outreach_log_id
    outreach_log = None

    if outreach_log_id:
        result = await session.execute(
            select(OutreachLog).where(OutreachLog.id == int(outreach_log_id))
        )
        outreach_log = result.scalar_one_or_none()

    if not outreach_log and sg_message_id:
        # sg_message_id format is "xxxx.filter000" — extract the base ID
        base_id = sg_message_id.split(".")[0] if "." in sg_message_id else sg_message_id
        result = await session.execute(
            select(OutreachLog).where(
                OutreachLog.message_sid.in_([sg_message_id, base_id])
            )
        )
        outreach_log = result.scalar_one_or_none()

    if not outreach_log:
        # Also try matching by email on recent logs
        lead_result = await session.execute(
            select(Lead.id).where(Lead.email == email)
        )
        lead_ids = [r[0] for r in lead_result.all()]
        if lead_ids:
            result = await session.execute(
                select(OutreachLog)
                .where(OutreachLog.lead_id.in_(lead_ids))
                .order_by(OutreachLog.created_at.desc())
                .limit(1)
            )
            outreach_log = result.scalar_one_or_none()

    if not outreach_log:
        return  # Can't find a matching log — event is stored but not linked

    # Update outreach log status (only advance, never regress)
    new_status = EVENT_TO_STATUS.get(event_type)
    if new_status:
        # Only update if new status is "further along"
        status_order = [
            OutreachStatus.PENDING,
            OutreachStatus.SENT,
            OutreachStatus.DELIVERED,
            OutreachStatus.OPENED,
            OutreachStatus.CLICKED,
            OutreachStatus.REPLIED,
        ]

        current_idx = status_order.index(outreach_log.status) if outreach_log.status in status_order else -1
        new_idx = status_order.index(new_status) if new_status in status_order else -1

        if new_idx > current_idx:
            outreach_log.status = new_status

    # Update timestamps
    if event_type == "open" and not outreach_log.opened_at:
        outreach_log.opened_at = event_timestamp
    elif event_type == "click" and not outreach_log.clicked_at:
        outreach_log.clicked_at = event_timestamp
    elif event_type == "bounce":
        outreach_log.bounced_at = event_timestamp

    # Update lead status for bounces/unsubscribes/spam reports
    lead_update_status = ENGAGEMENT_LEAD_STATUS.get(event_type)
    if lead_update_status and outreach_log.lead_id:
        lead = await session.get(Lead, outreach_log.lead_id)
        if lead:
            lead.status = lead_update_status
            lead.notes = f"Auto-updated: {event_type} event" + (
                f" — {event.get('reason', '')}" if event.get("reason") else ""
            )

            # Auto-suppress on negative events
            if event_type in ("bounce", "spamreport", "unsubscribe", "dropped"):
                await suppression_service.suppress_email(
                    email=email,
                    reason=event_type if event_type != "dropped" else "bounce",
                    description=event.get("reason", "") or f"Auto-suppressed from {event_type} webhook event",
                    source="webhook",
                    lead_id=outreach_log.lead_id,
                    outreach_log_id=outreach_log.id,
                    campaign_id=outreach_log.campaign_id if hasattr(outreach_log, 'campaign_id') else None,
                    added_by="system",
                )


async def get_webhook_events(
    outreach_log_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Query stored webhook events for debugging/audit."""
    async with async_session() as session:
        query = select(WebhookEvent)

        if outreach_log_id:
            query = query.where(WebhookEvent.outreach_log_id == outreach_log_id)
        if lead_id:
            query = query.where(
                WebhookEvent.outreach_log_id.in_(
                    select(OutreachLog.id).where(OutreachLog.lead_id == lead_id)
                )
            )
        if event_type:
            query = query.where(WebhookEvent.event_type == event_type)

        query = query.order_by(WebhookEvent.created_at.desc()).limit(limit)
        result = await session.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "email": e.email,
                "outreach_log_id": e.outreach_log_id,
                "reason": e.reason,
                "url": e.url,
                "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
