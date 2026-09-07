"""
Official Portal router.
GET /official/queue
GET /official/applications/{application_id}
PUT /official/applications/{application_id}/review
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import AuthUser, require_official, require_official_or_admin
from core.supabase_client import supabase_admin
from models.application import (
    OfficialApplicationDetailResponse,
    OfficialQueueResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
)
from services import workflow_engine

router = APIRouter(prefix="/official", tags=["official"])

# RBAC field filters: which citizen-profile fields each official role may see.
_ROLE_VISIBLE_FIELDS = {
    "official_rto": ["name", "dob", "address", "linked_license"],
    "official_bank": ["name", "dob", "address", "linked_pan"],
    "admin": None,  # None = no filtering, full visibility
}


@router.get("/queue", response_model=OfficialQueueResponse)
async def get_queue(
    status_filter: str = Query("pending", alias="status"),
    sort: str = Query("sla_risk"),
    user: AuthUser = Depends(require_official),
):
    query = supabase_admin.table("applications").select("*, citizens(name), workflows(service_name)")

    if status_filter == "pending":
        query = query.in_("status", ["pending_review", "in_progress"])
    else:
        query = query.eq("status", status_filter)

    result = query.execute()

    applications = []
    for row in result.data or []:
        applications.append(
            {
                "application_id": row["id"],
                "citizen_name": (row.get("citizens") or {}).get("name", "Unknown"),
                "service_name": (row.get("workflows") or {}).get("service_name", "Unknown"),
                "current_step": row["current_step"],
                "submitted_at": row["created_at"],
                "sla_deadline": row.get("sla_deadline"),
                "risk_flags": (row.get("data_json") or {}).get("risk_flags", []),
            }
        )

    if sort == "sla_risk":
        applications.sort(key=lambda a: (a["sla_deadline"] is None, a["sla_deadline"]))

    return OfficialQueueResponse(applications=applications)


@router.get("/applications/{application_id}", response_model=OfficialApplicationDetailResponse)
async def get_official_application_detail(application_id: str, user: AuthUser = Depends(require_official)):
    application = await workflow_engine.get_application(application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    citizen = (
        supabase_admin.table("citizens")
        .select("*")
        .eq("id", application["citizen_id"])
        .maybe_single()
        .execute()
    )
    citizen_data = citizen.data or {}

    visible_fields = _ROLE_VISIBLE_FIELDS.get(user.role)
    if visible_fields is not None:
        citizen_data = {k: v for k, v in citizen_data.items() if k in visible_fields}

    data_json = application.get("data_json") or {}
    ml_scores = {
        step_name: step_result.get("ml_result")
        for step_name, step_result in data_json.items()
        if isinstance(step_result, dict) and step_result.get("ml_result")
    }

    return OfficialApplicationDetailResponse(
        application_id=application["id"],
        workflow=application.get("workflows") or {},
        current_step=application["current_step"],
        status=application["status"],
        step_history=application.get("step_history") or [],
        data_json=data_json,
        ml_scores=ml_scores,
        citizen_profile=citizen_data,
    )


@router.put("/applications/{application_id}/review", response_model=ReviewDecisionResponse)
async def review_application(
    application_id: str,
    payload: ReviewDecisionRequest,
    user: AuthUser = Depends(require_official_or_admin),
):
    try:
        result = await workflow_engine.official_review(application_id, user.user_id, payload.action, payload.notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return ReviewDecisionResponse(**result)