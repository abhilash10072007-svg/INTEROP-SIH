"""
Centralized audit logging.

Every state-changing action across the backend (registration, application
review, role changes, consent decisions) should call `log_action` so
/admin/audit-logs has a complete trail. Kept as a thin wrapper around the
`audit_logs` table rather than inline inserts, so the schema can change in
one place.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from core.supabase_client import supabase_admin


async def log_action(
    actor_id: Optional[str],
    action: str,
    target_citizen_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Insert a row into audit_logs. Never raises — audit logging should not
    break the primary request if it fails; log to stdout instead."""
    try:
        supabase_admin.table("audit_logs").insert(
            {
                "actor_id": actor_id,
                "action": action,
                "target_citizen_id": target_citizen_id,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001 - audit failures must not break the request
        print(f"[audit_service] failed to log action '{action}': {exc}")


async def get_audit_logs(
    citizen_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = supabase_admin.table("audit_logs").select("*").order("timestamp", desc=True).limit(limit)

    if citizen_id:
        query = query.eq("target_citizen_id", citizen_id)
    if actor_id:
        query = query.eq("actor_id", actor_id)
    if action_type:
        query = query.eq("action", action_type)
    if from_date:
        query = query.gte("timestamp", from_date)
    if to_date:
        query = query.lte("timestamp", to_date)

    result = query.execute()
    return result.data or []