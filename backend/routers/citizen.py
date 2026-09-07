"""
Citizen Profile & Golden Record router.
GET  /citizen/profile
PUT  /citizen/profile
POST /citizen/link-records
GET  /citizen/documents
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthUser, require_citizen
from core.supabase_client import supabase_admin
from models.citizen import (
    CitizenDocumentsResponse,
    CitizenProfile,
    CitizenProfileUpdate,
    LinkRecordsRequest,
    LinkRecordsResponse,
)
from services import digilocker_mock
from services.audit_service import log_action

router = APIRouter(prefix="/citizen", tags=["citizen"])


def _get_citizen_or_404(citizen_id: str) -> dict:
    result = supabase_admin.table("citizens").select("*").eq("id", citizen_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citizen record not found")
    return result.data


@router.get("/profile", response_model=CitizenProfile)
async def get_profile(user: AuthUser = Depends(require_citizen)):
    citizen = _get_citizen_or_404(user.citizen_id)
    return CitizenProfile(
        citizen_id=citizen["id"],
        name=citizen["name"],
        dob=citizen["dob"],
        address=citizen["address"],
        linked_pan=citizen.get("linked_pan"),
        linked_voter_id=citizen.get("linked_voter_id"),
        linked_udyam=citizen.get("linked_udyam"),
        linked_license=citizen.get("linked_license"),
        verification_status=citizen["verification_status"],
    )


@router.put("/profile", response_model=CitizenProfile)
async def update_profile(payload: CitizenProfileUpdate, user: AuthUser = Depends(require_citizen)):
    _get_citizen_or_404(user.citizen_id)

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No editable fields provided")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase_admin.table("citizens").update(updates).eq("id", user.citizen_id).execute()
    updated = result.data[0]

    await log_action(actor_id=user.user_id, action="profile_updated", target_citizen_id=user.citizen_id,
                      details={"fields": list(updates.keys())})

    return CitizenProfile(
        citizen_id=updated["id"],
        name=updated["name"],
        dob=updated["dob"],
        address=updated["address"],
        linked_pan=updated.get("linked_pan"),
        linked_voter_id=updated.get("linked_voter_id"),
        linked_udyam=updated.get("linked_udyam"),
        linked_license=updated.get("linked_license"),
        verification_status=updated["verification_status"],
    )


@router.post("/link-records", response_model=LinkRecordsResponse)
async def link_records(payload: LinkRecordsRequest, user: AuthUser = Depends(require_citizen)):
    citizen = _get_citizen_or_404(user.citizen_id)

    try:
        gov_record = await digilocker_mock.lookup_gov_record(payload.document_type, payload.document_number)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not gov_record:
        return LinkRecordsResponse(linked=False, confidence_score=0.0)

    from core.ml_client import ml_client, MLServiceError

    try:
        match_result = await ml_client.fuzzy_match(
            name1=citizen["name"],
            address1=citizen["address"],
            name2=gov_record["name"],
            address2=gov_record.get("address", citizen["address"]),
        )
        confidence = match_result.get("confidence", 0.0)
        is_match = match_result.get("is_likely_match", False)
    except MLServiceError:
        confidence, is_match = 0.0, False

    if is_match:
        field_map = {"pan": "linked_pan", "voter_id": "linked_voter_id", "udyam": "linked_udyam", "license": "linked_license"}
        column = field_map.get(payload.document_type)
        if column:
            supabase_admin.table("citizens").update({column: payload.document_number}).eq("id", user.citizen_id).execute()

    await log_action(actor_id=user.user_id, action="link_records_attempted", target_citizen_id=user.citizen_id,
                      details={"document_type": payload.document_type, "linked": is_match, "confidence": confidence})

    return LinkRecordsResponse(linked=is_match, confidence_score=confidence)


@router.get("/documents", response_model=CitizenDocumentsResponse)
async def get_documents(user: AuthUser = Depends(require_citizen)):
    citizen = _get_citizen_or_404(user.citizen_id)
    return CitizenDocumentsResponse(documents=citizen.get("documents") or [])