"""Health check endpoints for monitoring, load balancers, and Docker healthchecks."""

import time
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.models import async_session

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check():
    """Basic health check — is the server alive?"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check — is the server ready to handle requests?

    Checks database and Redis connectivity.
    """
    checks = {}

    # Check database
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Redis (via Celery)
    try:
        from app.tasks import celery_app
        inspect = celery_app.control.inspect(timeout=3)
        active = inspect.active()
        checks["redis"] = "ok" if active is not None else "ok (no active workers)"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    all_ok = all(v.startswith("ok") for v in checks.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check — is the process healthy?

    Used by Kubernetes/Docker to decide whether to restart.
    """
    return {"status": "alive"}
