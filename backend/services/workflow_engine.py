"""
Workflow engine.

Drives an application through the steps defined for its workflow
(`workflows` + `workflow_steps` tables, seeded by the database team). Each
step is either "auto" (validated/decided server-side, possibly calling the
ML service) or "manual" (requires an official's review via
PUT /official/applications/{id}/review).

This module is intentionally the one place that knows how to move an
application from step N to step N+1, so routers stay thin.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from core.ml_client import ml_client, MLServiceError
from core.supabase_client import supabase_admin
from services.audit_service import log_action


async def get_workflow_steps(workflow_id: str) -> list[dict[str, Any]]:
    result = (
        supabase_admin.table("workflow_steps")
        .select("*")
        .eq("workflow_id", workflow_id)
        .order("step_order")
        .execute()
    )
    return result.data or []


async def create_application(citizen_id: str, workflow_id: str) -> dict[str, Any]:
    workflow = (
        supabase_admin.table("workflows")
        .select("*")
        .eq("id", workflow_id)
        .maybe_single()
        .execute()
    )
    if not workflow.data:
        raise ValueError("Unknown workflow_id")

    now = datetime.now(timezone.utc).isoformat()
    result = (
        supabase_admin.table("applications")
        .insert(
            {
                "citizen_id": citizen_id,
                "workflow_id": workflow_id,
                "current_step": 1,
                "status": "in_progress",
                "data_json": {},
                "step_history": [],
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    application = result.data[0]
    await log_action(actor_id=citizen_id, action="application_created", target_citizen_id=citizen_id,
                      details={"application_id": application["id"], "workflow_id": workflow_id})
    return application


async def list_citizen_applications(citizen_id: str) -> list[dict[str, Any]]:
    result = (
        supabase_admin.table("applications")
        .select("*, workflows(service_name)")
        .eq("citizen_id", citizen_id)
        .order("updated_at", desc=True)
        .execute()
    )
    applications = []
    for row in result.data or []:
        applications.append(
            {
                "application_id": row["id"],
                "service_name": (row.get("workflows") or {}).get("service_name", "Unknown"),
                "status": row["status"],
                "current_step": row["current_step"],
                "updated_at": row["updated_at"],
            }
        )
    return applications


async def get_application(application_id: str) -> Optional[dict[str, Any]]:
    result = (
        supabase_admin.table("applications")
        .select("*, workflows(id, service_name)")
        .eq("id", application_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def _run_auto_step(application: dict[str, Any], step: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """
    Executes an "auto" step. `step["step_name"]` determines which ML call (if any)
    to make. Unrecognized auto steps just pass validation data through.
    Returns a dict merged into the application's data_json under the step name.
    """
    step_name = step["step_name"]
    result: dict[str, Any] = {"input": data}

    try:
        if step_name == "risk_assessment":
            ml_result = await ml_client.risk_score(
                age=data.get("age", 0),
                income=data.get("income", 0),
                existing_loans=data.get("existing_loans", 0),
                avg_monthly_txn=data.get("avg_monthly_txn", 0),
                txn_stability_score=data.get("txn_stability_score", 0),
                business_type=data.get("business_type", "unknown"),
            )
            result["ml_result"] = ml_result
        elif step_name == "fraud_check":
            ml_result = await ml_client.fraud_check(
                citizen_id=application["citizen_id"],
                application_metadata=data,
            )
            result["ml_result"] = ml_result
        elif step_name == "fuzzy_match":
            ml_result = await ml_client.fuzzy_match(
                name1=data.get("name1", ""),
                address1=data.get("address1", ""),
                name2=data.get("name2", ""),
                address2=data.get("address2", ""),
            )
            result["ml_result"] = ml_result
        # else: generic auto step with no ML call, data recorded as-is
    except MLServiceError as exc:
        # Auto steps degrade to manual review if the ML service is down, rather
        # than blocking the citizen entirely.
        result["ml_error"] = exc.message
        result["fallback"] = "manual_review"

    return result


async def advance_step(application_id: str, step_order: int, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validates + advances the workflow for `application_id`.
    Returns {"current_step", "status", "message"}.
    """
    application = await get_application(application_id)
    if not application:
        raise ValueError("Application not found")
    if application["status"] not in ("in_progress",):
        raise ValueError(f"Application is '{application['status']}' and cannot be advanced")
    if step_order != application["current_step"]:
        raise ValueError(
            f"Step mismatch: application is at step {application['current_step']}, got {step_order}"
        )

    workflow_id = application["workflow_id"]
    steps = await get_workflow_steps(workflow_id)
    step_map = {s["step_order"]: s for s in steps}
    current = step_map.get(step_order)
    if not current:
        raise ValueError(f"No workflow step definition for step_order {step_order}")

    step_result: dict[str, Any] = {"data": data}
    new_status = application["status"]
    message = f"Step {step_order} ({current['step_name']}) recorded."

    if current["auto_or_manual"] == "auto":
        step_result = await _run_auto_step(application, current, data)
        if step_result.get("fallback") == "manual_review":
            message = f"Step {step_order} ({current['step_name']}) requires manual review (ML unavailable)."

    next_step_order = step_order + 1
    is_last_step = next_step_order not in step_map

    data_json = dict(application.get("data_json") or {})
    data_json[current["step_name"]] = step_result

    step_history = list(application.get("step_history") or [])
    step_history.append(
        {
            "step_order": step_order,
            "step_name": current["step_name"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "result": step_result,
        }
    )

    updates: dict[str, Any] = {
        "data_json": data_json,
        "step_history": step_history,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if is_last_step:
        # Last step auto-completes only if it was an auto step; manual last steps
        # wait for an official's review via /official/applications/{id}/review.
        if current["auto_or_manual"] == "auto":
            new_status = "completed"
            message = "Application completed."
        else:
            new_status = "pending_review"
            message = f"Step {step_order} submitted, awaiting official review."
        updates["status"] = new_status
    else:
        updates["current_step"] = next_step_order
        # If the next step is manual, park the application in pending_review so
        # it shows up in the official queue.
        if step_map[next_step_order]["auto_or_manual"] == "manual":
            new_status = "pending_review"
            updates["status"] = new_status
            message = f"Step {step_order} complete. Awaiting official review before step {next_step_order}."

    supabase_admin.table("applications").update(updates).eq("id", application_id).execute()

    await log_action(
        actor_id=application["citizen_id"],
        action="application_step_advanced",
        target_citizen_id=application["citizen_id"],
        details={"application_id": application_id, "step_order": step_order, "new_status": new_status},
    )

    return {
        "current_step": updates.get("current_step", application["current_step"]),
        "status": new_status,
        "message": message,
    }


async def withdraw_application(application_id: str, citizen_id: str) -> None:
    application = await get_application(application_id)
    if not application:
        raise ValueError("Application not found")
    if application["citizen_id"] != citizen_id:
        raise PermissionError("This application does not belong to the current citizen")

    supabase_admin.table("applications").update(
        {"status": "withdrawn", "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", application_id).execute()

    await log_action(actor_id=citizen_id, action="application_withdrawn", target_citizen_id=citizen_id,
                      details={"application_id": application_id})


async def official_review(application_id: str, official_id: str, action: str, notes: Optional[str]) -> dict[str, Any]:
    """
    PUT /official/applications/{id}/review equivalent.
    action: "approve" | "reject" | "request_info"
    """
    if action not in ("approve", "reject", "request_info"):
        raise ValueError("action must be 'approve', 'reject', or 'request_info'")

    application = await get_application(application_id)
    if not application:
        raise ValueError("Application not found")

    workflow_id = application["workflow_id"]
    steps = await get_workflow_steps(workflow_id)
    step_map = {s["step_order"]: s for s in steps}
    current_step_order = application["current_step"]
    is_last_step = (current_step_order + 1) not in step_map

    step_history = list(application.get("step_history") or [])
    step_history.append(
        {
            "step_order": current_step_order,
            "reviewed_by": official_id,
            "action": action,
            "notes": notes,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    updates: dict[str, Any] = {
        "step_history": step_history,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if action == "reject":
        new_status = "rejected"
        message = "Application rejected."
    elif action == "request_info":
        new_status = "info_requested"
        message = "Additional information requested from citizen."
    else:  # approve
        if is_last_step:
            new_status = "completed"
            message = "Application approved and completed."
        else:
            new_status = "in_progress"
            updates["current_step"] = current_step_order + 1
            message = f"Step {current_step_order} approved. Advanced to step {current_step_order + 1}."

    updates["status"] = new_status
    supabase_admin.table("applications").update(updates).eq("id", application_id).execute()

    notif_message = {
        "approve": f"Your application step {current_step_order} was approved.",
        "reject": "Your application was rejected. Please check the notes for details.",
        "request_info": "The reviewing official has requested more information on your application.",
    }[action]
    supabase_admin.table("notifications").insert(
        {
            "citizen_id": application["citizen_id"],
            "message": notif_message,
            "read_status": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    await log_action(actor_id=official_id, action=f"application_{action}", target_citizen_id=application["citizen_id"],
                      details={"application_id": application_id, "notes": notes})

    return {"status": new_status, "message": message}