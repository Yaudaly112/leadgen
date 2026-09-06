"""Task management routes for triggering background jobs."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.tasks import (
    batch_enrich_task,
    batch_generate_demos_task,
    discover_leads_task,
    enrich_lead_task,
    generate_demo_task,
    send_cold_email_task,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class DiscoverRequest(BaseModel):
    campaign_id: int
    category: str
    city: str
    state: str


@router.post("/discover")
async def trigger_discovery(data: DiscoverRequest):
    """Queue lead discovery as a background task."""
    task = discover_leads_task.delay(
        data.campaign_id, data.category, data.city, data.state
    )
    return {"task_id": task.id, "status": "queued"}


@router.post("/enrich/{lead_id}")
async def trigger_enrich(lead_id: int):
    """Queue enrichment for a single lead."""
    task = enrich_lead_task.delay(lead_id)
    return {"task_id": task.id, "lead_id": lead_id, "status": "queued"}


@router.post("/enrich-batch/{campaign_id}")
async def trigger_batch_enrich(campaign_id: int):
    """Queue batch enrichment for a campaign."""
    task = batch_enrich_task.delay(campaign_id)
    return {"task_id": task.id, "campaign_id": campaign_id, "status": "queued"}


@router.post("/generate-demo/{lead_id}")
async def trigger_demo_generation(lead_id: int):
    """Queue demo site generation for a lead."""
    task = generate_demo_task.delay(lead_id)
    return {"task_id": task.id, "lead_id": lead_id, "status": "queued"}


@router.post("/generate-demos-batch/{campaign_id}")
async def trigger_batch_demos(campaign_id: int):
    """Queue batch demo generation for a campaign."""
    task = batch_generate_demos_task.delay(campaign_id)
    return {"task_id": task.id, "campaign_id": campaign_id, "status": "queued"}


@router.post("/send-email/{lead_id}")
async def trigger_send_email(lead_id: int):
    """Queue cold email for a lead."""
    task = send_cold_email_task.delay(lead_id)
    return {"task_id": task.id, "lead_id": lead_id, "status": "queued"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a background task."""
    from app.tasks import celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
    }
