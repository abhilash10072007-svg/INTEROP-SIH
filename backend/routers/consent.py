"""
Consent Management router.
POST /consent/request
POST /consent/approve
GET  /consent/logs
GET  /consent/pending
"""
from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthUser, require_citizen, require_official_or_admin
from models.consent import (
    ConsentApproveRequest,
    ConsentLogsResponse,
    ConsentPendingResponse,
    ConsentRequestCreate,
    ConsentRequestResponse,
    ConsentStatusResponse,
)
from services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


@router.post("/request", response_model=ConsentRequestResponse)
async def request_consent(payload: ConsentRequestCreate, user: AuthUser = Depends(require_official_or_admin)):
    consent_id = await consent_service.create_consent_request(
        citizen_id=payload.citizen_id,
        requested_by=payload.requested_by,
        data_scope=payload.data_scope,
        purpose=payload.purpose,
    )
    return ConsentRequestResponse(consent_id=consent_id)


@router.post("/approve", response_model=ConsentStatusResponse)
async def approve_consent(payload: ConsentApproveRequest, user: AuthUser = Depends(require_citizen)):
    try:
        new_status = await consent_service.decide_consent(payload.consent_id, user.citizen_id, payload.approve)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return ConsentStatusResponse(status=new_status)


@router.get("/logs", response_model=ConsentLogsResponse)
async def get_consent_logs(user: AuthUser = Depends(require_citizen)):
    logs = await consent_service.get_citizen_consent_logs(user.citizen_id)
    return ConsentLogsResponse(logs=logs)


@router.get("/pending", response_model=ConsentPendingResponse)
async def get_pending_consents(user: AuthUser = Depends(require_citizen)):
    pending = await consent_service.get_pending_consent_requests(user.citizen_id)
    return ConsentPendingResponse(pending_requests=pending)