"""Celery tasks for background processing."""

import asyncio
from celery import Celery
from app.config import settings


def run_async(coro):
    """Run an async coroutine from sync Celery tasks."""
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


celery_app = Celery("leadgen", broker=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min timeout per task
    task_soft_time_limit=240,
)


@celery_app.task(bind=True, max_retries=3)
def discover_leads_task(self, campaign_id: int, category: str, city: str, state: str):
    """Background task for lead discovery."""
    import asyncio
    from app.agents.pipeline import pipeline

    async def run():
        return await pipeline.discover_leads(campaign_id, category, city, state)

    return run_async(run())


@celery_app.task(bind=True, max_retries=3)
def enrich_lead_task(self, lead_id: int):
    """Background task for enriching a single lead."""
    from app.agents.pipeline import pipeline

    async def run():
        return await pipeline.enrich_lead(lead_id)

    return run_async(run())


@celery_app.task(bind=True, max_retries=3)
def generate_demo_task(self, lead_id: int):
    """Background task for generating a demo site."""
    from app.agents.pipeline import pipeline

    async def run():
        return await pipeline.generate_demo(lead_id)

    return run_async(run())


@celery_app.task(bind=True, max_retries=3)
def send_cold_email_task(self, lead_id: int):
    """Background task for sending cold email."""
    from app.agents.pipeline import pipeline

    async def run():
        return await pipeline.send_cold_email(lead_id)

    return run_async(run())


@celery_app.task
def batch_enrich_task(campaign_id: int):
    """Batch enrich all discovered leads in a campaign."""
    from sqlalchemy import select
    from app.models import Lead, LeadStatus, async_session

    async def run():
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.status == LeadStatus.DISCOVERED,
                )
            )
            leads = result.scalars().all()

        for lead in leads:
            enrich_lead_task.delay(lead.id)

        return {"total": len(leads), "tasks_queued": len(leads)}

    return run_async(run())


@celery_app.task
def batch_generate_demos_task(campaign_id: int):
    """Batch generate demos for all enriched leads."""
    from sqlalchemy import select
    from app.models import Lead, LeadStatus, async_session

    async def run():
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.status == LeadStatus.ENRICHED,
                )
            )
            leads = result.scalars().all()

        for lead in leads:
            generate_demo_task.delay(lead.id)

        return {"total": len(leads), "tasks_queued": len(leads)}

    return run_async(run())


# ── Full Pipeline Runner ─────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=1)
def run_full_pipeline_task(self, run_id: int):
    """Execute the full pipeline (discover → enrich → demo → email) in background.

    This is the main task kicked off by the 'Run Pipeline' button.
    """
    from app.agents.pipeline import pipeline

    async def run():
        return await pipeline.run_full_pipeline(run_id)

    try:
        return run_async(run())
    except Exception as exc:
        # Update run as failed if the task crashes entirely
        run_async(_mark_run_failed(run_id, str(exc)))
        raise


async def _mark_run_failed(run_id: int, error: str):
    import json
    from datetime import datetime
    from app.models import PipelineRun, async_session

    async with async_session() as session:
        run = await session.get(PipelineRun, run_id)
        if run:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_log = json.dumps([{"error": error}])
            await session.commit()
# Mon Sep  7 02:28:11 SAST 2026
