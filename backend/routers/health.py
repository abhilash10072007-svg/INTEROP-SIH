"""
System / Health router.
GET /health
"""
from fastapi import APIRouter

from core.ml_client import ml_client
from core.supabase_client import supabase_admin
from models.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    ml_reachable = await ml_client.health()

    db_reachable = True
    try:
        supabase_admin.table("workflows").select("id").limit(1).execute()
    except Exception:  # noqa: BLE001
        db_reachable = False

    return HealthResponse(
        status="ok" if (ml_reachable and db_reachable) else "degraded",
        ml_service_reachable=ml_reachable,
        db_reachable=db_reachable,
    )