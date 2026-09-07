"""
Admin Portal router.
GET /admin/audit-logs
GET /admin/data-quality-flags
GET /admin/users
PUT /admin/users/{user_id}/role
GET /dashboard/analytics
"""
from collections import Counter
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.auth import AuthUser, require_admin, require_official_or_admin
from core.supabase_client import supabase_admin
from models.application import AdminUsersResponse, AnalyticsResponse, DataQualityFlagsResponse, UpdateUserRoleRequest
from models.common import AuditLogEntry, MessageResponse
from services import audit_service

router = APIRouter(tags=["admin"])


@router.get("/admin/audit-logs", response_model=list[AuditLogEntry])
async def get_audit_logs(
    citizen_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    action_type: Optional[str] = None,
    user: AuthUser = Depends(require_admin),
):
    logs = await audit_service.get_audit_logs(citizen_id, actor_id, from_date, to_date, action_type)
    return logs


@router.get("/admin/data-quality-flags", response_model=DataQualityFlagsResponse)
async def get_data_quality_flags(user: AuthUser = Depends(require_admin)):
    flags = []

    low_matches = (
        supabase_admin.table("audit_logs")
        .select("*")
        .eq("action", "link_records_attempted")
        .execute()
    )
    for row in low_matches.data or []:
        details = row.get("details") or {}
        confidence = details.get("confidence")
        if confidence is not None and confidence < 0.7:
            flags.append(
                {
                    "citizen_id": row["target_citizen_id"],
                    "issue_type": "low_fuzzy_match",
                    "confidence_score": confidence,
                    "flagged_at": row["timestamp"],
                }
            )

    citizens_with_flags = (
        supabase_admin.table("citizens")
        .select("id, verification_status")
        .neq("verification_status", "verified")
        .execute()
    )
    for row in citizens_with_flags.data or []:
        flags.append(
            {
                "citizen_id": row["id"],
                "issue_type": "ocr_tamper_flag" if row["verification_status"] == "flagged" else "fraud_flag",
                "confidence_score": None,
                "flagged_at": datetime.utcnow().isoformat(),
            }
        )

    return DataQualityFlagsResponse(flags=flags)


@router.get("/admin/users", response_model=AdminUsersResponse)
async def list_users(user: AuthUser = Depends(require_admin)):
    result = supabase_admin.table("profiles").select("*").execute()
    return AdminUsersResponse(users=result.data or [])


@router.put("/admin/users/{user_id}/role", response_model=MessageResponse)
async def update_user_role(user_id: str, payload: UpdateUserRoleRequest, user: AuthUser = Depends(require_admin)):
    supabase_admin.table("profiles").update({"role": payload.role}).eq("id", user_id).execute()
    await audit_service.log_action(actor_id=user.user_id, action="user_role_updated",
                                     details={"target_user_id": user_id, "new_role": payload.role})
    return MessageResponse(status="ok", message=f"User {user_id} role updated to '{payload.role}'.")


@router.get("/dashboard/analytics", response_model=AnalyticsResponse)
async def get_dashboard_analytics(
    service: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),
    user: AuthUser = Depends(require_official_or_admin),
):
    query = supabase_admin.table("applications").select("*, workflows(service_name)")
    result = query.execute()
    rows = result.data or []

    if service:
        rows = [r for r in rows if (r.get("workflows") or {}).get("service_name") == service]

    total_applications = len(rows)
    by_status = Counter(r["status"] for r in rows)
    by_service = Counter((r.get("workflows") or {}).get("service_name", "Unknown") for r in rows)

    processing_days = []
    sla_breach_count = 0
    ml_auto_approved_count = 0
    manual_review_count = 0
    by_date = Counter()

    for r in rows:
        created = r.get("created_at")
        updated = r.get("updated_at")
        if created and updated and r["status"] == "completed":
            try:
                delta = datetime.fromisoformat(updated.replace("Z", "+00:00")) - datetime.fromisoformat(created.replace("Z", "+00:00"))
                processing_days.append(delta.total_seconds() / 86400)
            except (ValueError, TypeError):
                pass

        sla_deadline = r.get("sla_deadline")
        if sla_deadline and r["status"] not in ("completed",):
            try:
                if datetime.fromisoformat(sla_deadline.replace("Z", "+00:00")) < datetime.utcnow():
                    sla_breach_count += 1
            except (ValueError, TypeError):
                pass

        data_json = r.get("data_json") or {}
        for step_result in data_json.values():
            if isinstance(step_result, dict):
                ml_result = step_result.get("ml_result")
                if ml_result and ml_result.get("recommendation") == "auto_approve":
                    ml_auto_approved_count += 1
                elif step_result.get("fallback") == "manual_review":
                    manual_review_count += 1

        if created:
            by_date[created[:10]] += 1

    avg_processing_time_days = round(sum(processing_days) / len(processing_days), 2) if processing_days else 0.0

    return AnalyticsResponse(
        total_applications=total_applications,
        by_status=dict(by_status),
        by_service=dict(by_service),
        avg_processing_time_days=avg_processing_time_days,
        sla_breach_count=sla_breach_count,
        ml_auto_approved_count=ml_auto_approved_count,
        manual_review_count=manual_review_count,
        applications_over_time=[{"date": d, "count": c} for d, c in sorted(by_date.items())],
    )