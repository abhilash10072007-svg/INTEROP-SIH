"""Business logic for consent_logs: requesting, approving/denying, and reading history."""
from datetime import datetime, timezone
from typing import Any, Optional

from core.supabase_client import supabase_admin
from services.audit_service import log_action


async def create_consent_request(citizen_id: str, requested_by: str, data_scope: str, purpose: str) -> str:
    result = (
        supabase_admin.table("consent_logs")
        .insert(
            {
                "citizen_id": citizen_id,
                "requested_by": requested_by,
                "data_scope": data_scope,
                "purpose": purpose,
                "status": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    consent_id = result.data[0]["id"]
    await log_action(actor_id=requested_by, action="consent_requested", target_citizen_id=citizen_id,
                      details={"consent_id": consent_id, "data_scope": data_scope, "purpose": purpose})
    return consent_id


async def decide_consent(consent_id: str, citizen_id: str, approve: bool) -> str:
    """Citizen approves/denies a pending consent request. Returns the new status."""
    existing = (
        supabase_admin.table("consent_logs")
        .select("*")
        .eq("id", consent_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise ValueError("Consent request not found")
    if existing.data["citizen_id"] != citizen_id:
        raise PermissionError("This consent request does not belong to the current citizen")
    if existing.data["status"] != "pending":
        raise ValueError(f"Consent request already '{existing.data['status']}'")

    new_status = "approved" if approve else "denied"
    supabase_admin.table("consent_logs").update({"status": new_status}).eq("id", consent_id).execute()

    await log_action(actor_id=citizen_id, action=f"consent_{new_status}", target_citizen_id=citizen_id,
                      details={"consent_id": consent_id})
    return new_status


async def get_citizen_consent_logs(citizen_id: str) -> list[dict[str, Any]]:
    result = (
        supabase_admin.table("consent_logs")
        .select("*")
        .eq("citizen_id", citizen_id)
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data or []


async def get_pending_consent_requests(citizen_id: str) -> list[dict[str, Any]]:
    result = (
        supabase_admin.table("consent_logs")
        .select("*")
        .eq("citizen_id", citizen_id)
        .eq("status", "pending")
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data or []