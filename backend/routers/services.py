"""
Service Catalog router.
GET /services
GET /services/{workflow_id}
"""
from fastapi import APIRouter, HTTPException, status

from core.supabase_client import supabase_admin
from models.application import ServiceDetailResponse, ServicesListResponse, ServiceSummary, WorkflowStep

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=ServicesListResponse)
async def list_services():
    workflows = supabase_admin.table("workflows").select("*").execute()
    services = []
    for wf in workflows.data or []:
        steps = (
            supabase_admin.table("workflow_steps")
            .select("id", count="exact")
            .eq("workflow_id", wf["id"])
            .execute()
        )
        services.append(
            ServiceSummary(
                workflow_id=wf["id"],
                service_name=wf["service_name"],
                description=wf.get("description"),
                steps_count=steps.count or 0,
            )
        )
    return ServicesListResponse(services=services)


@router.get("/{workflow_id}", response_model=ServiceDetailResponse)
async def get_service_detail(workflow_id: str):
    workflow = supabase_admin.table("workflows").select("*").eq("id", workflow_id).maybe_single().execute()
    if not workflow.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    steps_result = (
        supabase_admin.table("workflow_steps")
        .select("*")
        .eq("workflow_id", workflow_id)
        .order("step_order")
        .execute()
    )
    steps = [
        WorkflowStep(
            step_order=s["step_order"],
            step_name=s["step_name"],
            step_type=s["step_type"],
            auto_or_manual=s["auto_or_manual"],
        )
        for s in steps_result.data or []
    ]

    return ServiceDetailResponse(
        workflow_id=workflow.data["id"],
        service_name=workflow.data["service_name"],
        steps=steps,
    )