"""
Applications router.
POST   /applications
GET    /applications
GET    /applications/{application_id}
PUT    /applications/{application_id}/step
POST   /applications/{application_id}/upload-document
DELETE /applications/{application_id}
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from core.auth import AuthUser, require_citizen
from core.ml_client import MLServiceError, ml_client
from core.supabase_client import supabase_admin
from models.application import (
    AdvanceStepRequest,
    AdvanceStepResponse,
    ApplicationDetailResponse,
    ApplicationsListResponse,
    CreateApplicationRequest,
    CreateApplicationResponse,
    UploadDocumentResponse,
)
from models.common import MessageResponse
from services import workflow_engine

router = APIRouter(prefix="/applications", tags=["applications"])

STORAGE_BUCKET = "documents"


def _assert_owns_application(application: dict, citizen_id: str) -> None:
    if application["citizen_id"] != citizen_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This application does not belong to you")


@router.post("", response_model=CreateApplicationResponse)
async def create_application(payload: CreateApplicationRequest, user: AuthUser = Depends(require_citizen)):
    try:
        application = await workflow_engine.create_application(user.citizen_id, payload.workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return CreateApplicationResponse(
        application_id=application["id"],
        current_step=application["current_step"],
        status=application["status"],
    )


@router.get("", response_model=ApplicationsListResponse)
async def list_applications(user: AuthUser = Depends(require_citizen)):
    applications = await workflow_engine.list_citizen_applications(user.citizen_id)
    return ApplicationsListResponse(applications=applications)


@router.get("/{application_id}", response_model=ApplicationDetailResponse)
async def get_application_detail(application_id: str, user: AuthUser = Depends(require_citizen)):
    application = await workflow_engine.get_application(application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Citizens may only view their own; officials use /official/applications/{id} instead.
    if user.role == "citizen":
        _assert_owns_application(application, user.citizen_id)

    return ApplicationDetailResponse(
        application_id=application["id"],
        workflow=application.get("workflows") or {},
        current_step=application["current_step"],
        status=application["status"],
        step_history=application.get("step_history") or [],
        data_json=application.get("data_json") or {},
    )


@router.put("/{application_id}/step", response_model=AdvanceStepResponse)
async def advance_step(application_id: str, payload: AdvanceStepRequest, user: AuthUser = Depends(require_citizen)):
    application = await workflow_engine.get_application(application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    _assert_owns_application(application, user.citizen_id)

    try:
        result = await workflow_engine.advance_step(application_id, payload.step_order, payload.data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return AdvanceStepResponse(**result)


@router.post("/{application_id}/upload-document", response_model=UploadDocumentResponse)
async def upload_document(
    application_id: str,
    document_purpose: str = Form(...),
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_citizen),
):
    application = await workflow_engine.get_application(application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    _assert_owns_application(application, user.citizen_id)

    file_bytes = await file.read()
    storage_path = f"{user.citizen_id}/{application_id}/{uuid.uuid4()}_{file.filename}"

    supabase_admin.storage.from_(STORAGE_BUCKET).upload(
        storage_path, file_bytes, {"content-type": file.content_type or "application/octet-stream"}
    )
    file_url = supabase_admin.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

    ocr_result = None
    face_match_result = None

    try:
        if document_purpose in ("aadhaar", "pan", "voter_id", "medical_certificate", "license"):
            ocr_result = await ml_client.ocr_extract(file_bytes, file.filename, file.content_type or "image/jpeg")
        elif document_purpose == "selfie":
            # Face-match needs a second image (the ID photo already on file); callers
            # that want this should follow up with the id_photo separately if needed.
            pass
    except MLServiceError:
        pass

    supabase_admin.table("applications").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", application_id).execute()

    return UploadDocumentResponse(file_url=file_url, ocr_result=ocr_result, face_match_result=face_match_result)


@router.delete("/{application_id}", response_model=MessageResponse)
async def withdraw_application(application_id: str, user: AuthUser = Depends(require_citizen)):
    try:
        await workflow_engine.withdraw_application(application_id, user.citizen_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return MessageResponse(status="withdrawn", message="Application withdrawn successfully.")