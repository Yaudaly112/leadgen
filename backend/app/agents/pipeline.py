"""Agent pipeline orchestrates the full lead generation workflow."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func

from app.models import (
    Base,
    Campaign,
    Lead,
    LeadStatus,
    OutreachLog,
    OutreachStatus,
    OutreachType,
    PipelineRun,
    async_session,
)
from app.services.places import places_client
from app.services.llm import (
    generate_business_description,
    generate_call_script,
    generate_cold_email,
    generate_followup_email,
)
from app.services.demo_generator import demo_generator
from app.services.email_sender import email_sender
from app.services.suppression import suppression_service
from app.config import settings


class AgentPipeline:
    """Orchestrates the full lead generation pipeline."""

    async def discover_leads(
        self,
        campaign_id: int,
        category: str,
        city: str,
        state: str,
    ) -> list[dict]:
        """Step 1: Discover businesses without websites."""
        print(f"🔍 Discovering {category} businesses in {city}, {state}...")

        raw_leads = await places_client.find_businesses_without_websites(
            category=category,
            city=city,
            state=state,
        )

        print(f"  Found {len(raw_leads)} businesses without websites")

        # Save to database
        saved_leads = []
        async with async_session() as session:
            for lead_data in raw_leads:
                # Check if already exists
                existing = await session.execute(
                    select(Lead).where(
                        Lead.google_place_id == lead_data.get("google_place_id")
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                lead = Lead(
                    campaign_id=campaign_id,
                    status=LeadStatus.DISCOVERED,
                    **{k: v for k, v in lead_data.items() if hasattr(Lead, k)},
                )
                session.add(lead)
                await session.flush()
                saved_leads.append(lead)

            await session.commit()

        print(f"  Saved {len(saved_leads)} new leads")
        return saved_leads

    async def enrich_lead(self, lead_id: int) -> dict:
        """Step 2: Enrich a lead with AI-generated content."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            # Generate AI description
            business_data = {
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "city": lead.city,
                "state": lead.state,
                "rating": lead.rating,
                "review_count": lead.review_count,
                "services": lead.services.split(",") if lead.services else [],
            }

            lead.ai_description = await generate_business_description(business_data)
            lead.status = LeadStatus.ENRICHED

            await session.commit()
            return {"lead_id": lead_id, "status": "enriched"}

    async def generate_demo(self, lead_id: int) -> dict:
        """Step 3: Generate a demo website for the lead."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            business_data = {
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "city": lead.city,
                "state": lead.state,
                "phone": lead.phone,
                "rating": lead.rating,
                "review_count": lead.review_count,
                "services": lead.services.split(",") if lead.services else [],
            }

            result = await demo_generator.generate_site(business_data)

            lead.demo_url = result["demo_url"]
            lead.demo_template = result["slug"]
            lead.demo_generated_at = datetime.utcnow()
            lead.status = LeadStatus.DEMO_CREATED

            await session.commit()
            return {
                "lead_id": lead_id,
                "demo_url": result["demo_url"],
                "slug": result["slug"],
            }

    async def send_cold_email(self, lead_id: int) -> dict:
        """Step 4: Send the initial cold email.

        Creates the OutreachLog first (to get the log ID), then sends the
        email with the log ID as a custom arg so webhook events map back.
        Checks suppression list before sending.
        """
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            if not lead.email:
                return {"error": "No email address available"}

            # Check suppression list before generating/sending anything
            suppression = await suppression_service.is_suppressed(email=lead.email)
            if suppression["is_suppressed"]:
                lead.status = LeadStatus.DO_NOT_CONTACT
                lead.notes = f"Blocked by suppression: {suppression['matches'][0]['reason']}"
                await session.commit()
                return {
                    "error": "Suppressed",
                    "reason": suppression["matches"][0]["reason"],
                    "details": suppression["matches"],
                }

            business_data = {
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "city": lead.city,
                "state": lead.state,
                "rating": lead.rating,
                "review_count": lead.review_count,
            }

            # Generate personalized email
            email_content = await generate_cold_email(business_data, lead.demo_url)

            # Build HTML version
            html_body = email_sender.build_cold_email_html(
                body_text=email_content["body"],
                demo_url=lead.demo_url,
                business_name=lead.business_name,
                sender_name=settings.email_from_name,
                sender_company="Your Web Design Company",
                sender_phone="Your Phone",
                sender_address="Your Business Address, City, State ZIP",
                unsubscribe_url=settings.unsubscribe_url,
            )

            # Create log first so we have an ID to pass to SendGrid
            log = OutreachLog(
                lead_id=lead_id,
                outreach_type=OutreachType.EMAIL,
                status=OutreachStatus.PENDING,
                subject=email_content["subject"],
                body=email_content["body"],
                template_used="cold_email_v1",
                approved=False,
            )
            session.add(log)
            await session.flush()  # get the log ID without committing

            # If human review is required, stop here
            if settings.review_before_sending:
                lead.status = LeadStatus.OUTREACH_QUEUED
                await session.commit()
                return {
                    "status": "pending_approval",
                    "outreach_log_id": log.id,
                    "subject": email_content["subject"],
                    "body": email_content["body"],
                    "lead_id": lead_id,
                }

            # Send immediately — pass log ID so webhook events trace back
            result = await email_sender.send_email(
                to_email=lead.email,
                to_name=lead.business_name,
                subject=email_content["subject"],
                html_body=html_body,
                custom_args={
                    "lead_id": str(lead_id),
                    "outreach_log_id": str(log.id),
                },
            )

            log.status = OutreachStatus.SENT if result["success"] else OutreachStatus.FAILED
            log.message_sid = result.get("message_id")
            log.approved = True
            log.sent_at = datetime.utcnow()

            if result["success"]:
                lead.status = LeadStatus.EMAIL_SENT

            await session.commit()
            return {"outreach_log_id": log.id, **result}

    async def send_followup(self, lead_id: int, followup_number: int = 1) -> dict:
        """Step 5: Send a follow-up email. Checks suppression before sending."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead or not lead.email:
                return {"error": "Lead not found or no email"}

            # Check suppression before proceeding
            suppression = await suppression_service.is_suppressed(email=lead.email)
            if suppression["is_suppressed"]:
                lead.status = LeadStatus.DO_NOT_CONTACT
                lead.notes = f"Blocked by suppression: {suppression['matches'][0]['reason']}"
                await session.commit()
                return {
                    "error": "Suppressed",
                    "reason": suppression["matches"][0]["reason"],
                    "details": suppression["matches"],
                }

            business_data = {
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "city": lead.city,
                "state": lead.state,
            }

            email_content = await generate_followup_email(
                business_data, lead.demo_url, followup_number
            )

            html_body = email_sender.build_cold_email_html(
                body_text=email_content["body"],
                demo_url=lead.demo_url,
                business_name=lead.business_name,
                sender_name=settings.email_from_name,
                sender_company="Your Web Design Company",
                sender_phone="Your Phone",
                sender_address="Your Business Address, City, State ZIP",
                unsubscribe_url=settings.unsubscribe_url,
            )

            # Create log first to get ID for webhook tracking
            log = OutreachLog(
                lead_id=lead_id,
                outreach_type=OutreachType.FOLLOWUP_EMAIL,
                status=OutreachStatus.PENDING,
                subject=email_content["subject"],
                body=email_content["body"],
                template_used=f"followup_v{followup_number}",
                approved=False,
            )
            session.add(log)
            await session.flush()

            if settings.review_before_sending:
                await session.commit()
                return {"status": "pending_approval", "outreach_log_id": log.id, "lead_id": lead_id}

            result = await email_sender.send_email(
                to_email=lead.email,
                to_name=lead.business_name,
                subject=email_content["subject"],
                html_body=html_body,
                custom_args={
                    "lead_id": str(lead_id),
                    "outreach_log_id": str(log.id),
                },
            )

            log.status = OutreachStatus.SENT if result["success"] else OutreachStatus.FAILED
            log.message_sid = result.get("message_id")
            log.approved = True
            log.sent_at = datetime.utcnow()

            if result["success"]:
                lead.status = LeadStatus.FOLLOWUP_SENT

            await session.commit()
            return {"outreach_log_id": log.id, **result}

    async def generate_call_script(self, lead_id: int) -> str:
        """Generate a call script for manual calling."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            business_data = {
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "city": lead.city,
                "state": lead.state,
            }

            return await generate_call_script(business_data, lead.demo_url)

    async def approve_outreach(self, log_id: int, approved_by: str) -> dict:
        """Approve a pending outreach for sending. Checks suppression before sending."""
        async with async_session() as session:
            log = await session.get(OutreachLog, log_id)
            if not log:
                raise ValueError(f"Outreach log {log_id} not found")

            log.approved = True
            log.approved_by = approved_by
            log.approved_at = datetime.utcnow()

            if log.outreach_type in (OutreachType.EMAIL, OutreachType.FOLLOWUP_EMAIL):
                lead = await session.get(Lead, log.lead_id)
                if lead and lead.email:
                    # Check suppression before sending
                    suppression = await suppression_service.is_suppressed(email=lead.email)
                    if suppression["is_suppressed"]:
                        log.status = OutreachStatus.FAILED
                        log.body = (log.body or "") + f"\n\n[Suppressed: {suppression['matches'][0]['reason']} — not sent]"
                        lead.status = LeadStatus.DO_NOT_CONTACT
                        lead.notes = f"Blocked by suppression during approval: {suppression['matches'][0]['reason']}"
                        await session.commit()
                        return {"log_id": log_id, "status": "blocked_by_suppression", "reason": suppression["matches"][0]["reason"]}
                    # Build and send the email with log ID for webhook tracking
                    html_body = email_sender.build_cold_email_html(
                        body_text=log.body,
                        demo_url=lead.demo_url,
                        business_name=lead.business_name,
                        sender_name=settings.email_from_name,
                        sender_company="Your Web Design Company",
                        sender_phone="Your Phone",
                        sender_address="Your Business Address, City, State ZIP",
                        unsubscribe_url=settings.unsubscribe_url,
                    )

                    result = await email_sender.send_email(
                        to_email=lead.email,
                        to_name=lead.business_name,
                        subject=log.subject,
                        html_body=html_body,
                        custom_args={
                            "lead_id": str(lead.lead_id if hasattr(lead, 'lead_id') else lead.id),
                            "outreach_log_id": str(log.id),
                        },
                    )

                    log.status = OutreachStatus.SENT if result["success"] else OutreachStatus.FAILED
                    log.message_sid = result.get("message_id")
                    log.sent_at = datetime.utcnow()

                    if result["success"]:
                        lead.status = (
                            LeadStatus.EMAIL_SENT
                            if log.outreach_type == OutreachType.EMAIL
                            else LeadStatus.FOLLOWUP_SENT
                        )

            await session.commit()
            return {"log_id": log_id, "status": "approved_and_sent"}

    async def mark_not_interested(self, lead_id: int, reason: str = "") -> dict:
        """Mark a lead as not interested."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if lead:
                lead.status = LeadStatus.NOT_INTERESTED
                lead.notes = reason
                await session.commit()
        return {"lead_id": lead_id, "status": "marked_not_interested"}

    # ── Full Pipeline Runner ───────────────────────────────────────────────────

    async def run_full_pipeline(self, run_id: int) -> dict:
        """Execute the full pipeline: discover → enrich → demo → email.

        This is the main orchestrator called by the batch pipeline runner.
        It updates the PipelineRun record at each step so the frontend
        can poll for progress.
        """
        async with async_session() as session:
            run = await session.get(PipelineRun, run_id)
            if not run:
                raise ValueError(f"Pipeline run {run_id} not found")

            campaign = await session.get(Campaign, run.campaign_id)
            if not campaign:
                run.status = "failed"
                run.error_log = json.dumps([{"error": "Campaign not found"}])
                await session.commit()
                return {"error": "Campaign not found"}

            run.status = "running"
            run.started_at = datetime.utcnow()
            await session.commit()

        errors = []

        try:
            # ── Step 1: Discovery ──────────────────────────────────────────────
            if not run.skip_discovery:
                await self._update_run(run_id, discovery_status="running", discovery_started_at=datetime.utcnow())
                try:
                    leads = await self.discover_leads(
                        campaign_id=campaign.id,
                        category=campaign.target_category,
                        city=campaign.target_city,
                        state=campaign.target_state,
                    )
                    await self._update_run(
                        run_id,
                        discovery_status="completed",
                        discovery_new=len(leads),
                        discovery_completed_at=datetime.utcnow(),
                    )
                except Exception as e:
                    errors.append({"step": "discovery", "error": str(e)})
                    await self._update_run(
                        run_id,
                        discovery_status="failed",
                        discovery_error=str(e),
                        discovery_completed_at=datetime.utcnow(),
                    )
            else:
                await self._update_run(run_id, discovery_status="skipped")

            # ── Step 2: Enrichment ─────────────────────────────────────────────
            if not run.skip_enrichment:
                # Get leads that need enrichment
                leads_to_enrich = await self._get_leads_by_status(campaign.id, LeadStatus.DISCOVERED)
                await self._update_run(
                    run_id,
                    enrichment_status="running",
                    enrichment_total=len(leads_to_enrich),
                    enrichment_started_at=datetime.utcnow(),
                )

                enriched = 0
                enrich_errors = 0
                for i, lead in enumerate(leads_to_enrich):
                    try:
                        await self.enrich_lead(lead.id)
                        enriched += 1
                    except Exception as e:
                        enrich_errors += 1
                        errors.append({"step": "enrichment", "lead_id": lead.id, "error": str(e)})
                    # Update progress every 5 leads
                    if (i + 1) % 5 == 0 or i == len(leads_to_enrich) - 1:
                        await self._update_run(
                            run_id,
                            enrichment_done=enriched,
                            enrichment_errors=enrich_errors,
                        )

                await self._update_run(
                    run_id,
                    enrichment_status="completed" if enrich_errors == 0 else "completed",
                    enrichment_done=enriched,
                    enrichment_errors=enrich_errors,
                    enrichment_completed_at=datetime.utcnow(),
                )
            else:
                await self._update_run(run_id, enrichment_status="skipped")

            # ── Step 3: Demo Generation ────────────────────────────────────────
            if not run.skip_demo:
                leads_to_demo = await self._get_leads_by_status(campaign.id, LeadStatus.ENRICHED)
                await self._update_run(
                    run_id,
                    demo_status="running",
                    demo_total=len(leads_to_demo),
                    demo_started_at=datetime.utcnow(),
                )

                demos = 0
                demo_errors = 0
                for i, lead in enumerate(leads_to_demo):
                    try:
                        await self.generate_demo(lead.id)
                        demos += 1
                    except Exception as e:
                        demo_errors += 1
                        errors.append({"step": "demo", "lead_id": lead.id, "error": str(e)})
                    if (i + 1) % 5 == 0 or i == len(leads_to_demo) - 1:
                        await self._update_run(
                            run_id,
                            demo_done=demos,
                            demo_errors=demo_errors,
                        )

                await self._update_run(
                    run_id,
                    demo_status="completed",
                    demo_done=demos,
                    demo_errors=demo_errors,
                    demo_completed_at=datetime.utcnow(),
                )
            else:
                await self._update_run(run_id, demo_status="skipped")

            # ── Step 4: Email Outreach ─────────────────────────────────────────
            if not run.skip_email:
                leads_to_email = await self._get_leads_by_status(campaign.id, LeadStatus.DEMO_CREATED)
                await self._update_run(
                    run_id,
                    email_status="running",
                    email_total=len(leads_to_email),
                    email_started_at=datetime.utcnow(),
                )

                sent = 0
                queued = 0
                suppressed = 0
                email_errors = 0
                for i, lead in enumerate(leads_to_email):
                    try:
                        result = await self.send_cold_email(lead.id)
                        if result.get("status") == "pending_approval":
                            queued += 1
                        elif result.get("error") == "Suppressed":
                            suppressed += 1
                        elif result.get("success"):
                            sent += 1
                        else:
                            email_errors += 1
                    except Exception as e:
                        email_errors += 1
                        errors.append({"step": "email", "lead_id": lead.id, "error": str(e)})
                    if (i + 1) % 5 == 0 or i == len(leads_to_email) - 1:
                        await self._update_run(
                            run_id,
                            email_sent=sent,
                            email_queued=queued,
                            email_suppressed=suppressed,
                            email_errors=email_errors,
                        )

                await self._update_run(
                    run_id,
                    email_status="completed",
                    email_sent=sent,
                    email_queued=queued,
                    email_suppressed=suppressed,
                    email_errors=email_errors,
                    email_completed_at=datetime.utcnow(),
                )
            else:
                await self._update_run(run_id, email_status="skipped")

            # ── Finalize ───────────────────────────────────────────────────────
            run_status = "completed" if not errors else "completed_with_errors"
            await self._update_run(
                run_id,
                status=run_status,
                completed_at=datetime.utcnow(),
                error_log=json.dumps(errors) if errors else None,
            )

            # Update campaign stats
            async with async_session() as session:
                campaign = await session.get(Campaign, run.campaign_id)
                if campaign:
                    total_leads = await session.scalar(
                        select(func.count(Lead.id)).where(Lead.campaign_id == campaign.id)
                    ) or 0
                    emails_queued = await session.scalar(
                        select(func.count(OutreachLog.id))
                        .join(Lead)
                        .where(
                            Lead.campaign_id == campaign.id,
                            OutreachLog.status == OutreachStatus.PENDING,
                        )
                    ) or 0
                    campaign.total_leads = total_leads
                    campaign.emails_sent = emails_queued
                    campaign.status = "active"
                    await session.commit()

            return {
                "run_id": run_id,
                "status": run_status,
                "errors": errors,
            }

        except Exception as e:
            await self._update_run(
                run_id,
                status="failed",
                completed_at=datetime.utcnow(),
                error_log=json.dumps([{"error": str(e)}]),
            )
            return {"run_id": run_id, "status": "failed", "error": str(e)}

    async def _update_run(self, run_id: int, **kwargs):
        """Update a PipelineRun record."""
        async with async_session() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                for key, value in kwargs.items():
                    if hasattr(run, key):
                        setattr(run, key, value)
                run.updated_at = datetime.utcnow()
                await session.commit()

    async def _get_leads_by_status(self, campaign_id: int, status: LeadStatus) -> list:
        """Get all leads in a campaign with a given status."""
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.status == status,
                )
            )
            return list(result.scalars().all())


pipeline = AgentPipeline()
