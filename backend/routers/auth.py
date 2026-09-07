"""
Registration & Auth router.
POST /auth/pre-register
POST /auth/callback
POST /auth/login-request-otp
POST /auth/login-verify-otp
POST /auth/resend-otp
"""
import random
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, status

from core.auth import create_access_token, create_refresh_token
from core.config import settings
from core.supabase_client import supabase_admin
from models.citizen import (
    AuthCallbackRequest,
    DigilockerDocumentsResponse,
    DigilockerTokenRequest,
    DigilockerTokenResponse,
    LoginRequestOTP,
    LoginVerifyOTP,
    OTPSentResponse,
    OTPVerifyResponse,
    PreRegisterRequest,
    PreRegisterResponse,
    ResendOTPRequest,
    TokenResponse,
)
from services import digilocker_mock
from services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory OTP store for the demo: mobile -> {otp, expires_at}
_OTP_STORE: dict[str, dict] = {}
OTP_TTL_SECONDS = 300


@router.post("/pre-register", response_model=PreRegisterResponse)
async def pre_register(payload: PreRegisterRequest):
    """Stashes the registration form until the DigiLocker consent step confirms identity."""
    existing = (
        supabase_admin.table("citizens")
        .select("id")
        .eq("mobile", payload.mobile)
        .maybe_single()
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mobile number already registered")

    result = (
        supabase_admin.table("pending_registrations")
        .insert(
            {
                "full_name": payload.full_name,
                "mobile": payload.mobile,
                "email": payload.email,
                "dob": payload.dob.isoformat(),
                "aadhaar_number": payload.aadhaar_number,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    pending_id = result.data[0]["id"]
    await log_action(actor_id=None, action="pre_register", details={"pending_id": pending_id, "mobile": payload.mobile})
    return PreRegisterResponse(pending_id=pending_id)


@router.post("/callback", response_model=TokenResponse)
async def auth_callback(payload: AuthCallbackRequest):
    """
    Exchanges the DigiLocker consent `code` for a mock token, fetches issued
    documents, fuzzy-matches them against the pre-registration form, then
    creates a Supabase Auth user + citizens row + profiles row.
    """
    pending = (
        supabase_admin.table("pending_registrations")
        .select("*")
        .eq("id", payload.pending_id)
        .maybe_single()
        .execute()
    )
    if not pending.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown pending_id")

    try:
        token_data = await digilocker_mock.exchange_code_for_token(payload.code, payload.pending_id)
        documents = await digilocker_mock.fetch_issued_documents(token_data["access_token"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    aadhaar_doc = next((d for d in documents if d["doc_type"] == "aadhaar"), None)
    if not aadhaar_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DigiLocker returned no Aadhaar document")

    # Fuzzy-match DigiLocker identity against the pre-registration form.
    try:
        from core.ml_client import ml_client, MLServiceError

        match_result = await ml_client.fuzzy_match(
            name1=pending.data["full_name"],
            address1=aadhaar_doc["address"],
            name2=aadhaar_doc["name"],
            address2=aadhaar_doc["address"],
        )
        if not match_result.get("is_likely_match", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identity details do not match DigiLocker records closely enough",
            )
    except MLServiceError:
        # ML service down: don't block registration in a demo, just skip the check.
        pass

    email = pending.data["email"]
    demo_password = secrets.token_urlsafe(18)

    auth_user = supabase_admin.auth.admin.create_user(
        {"email": email, "password": demo_password, "email_confirm": True}
    )
    user_id = auth_user.user.id

    supabase_admin.table("profiles").insert(
        {"id": user_id, "name": pending.data["full_name"], "email": email, "role": "citizen",
         "created_at": datetime.now(timezone.utc).isoformat()}
    ).execute()

    citizen_result = (
        supabase_admin.table("citizens")
        .insert(
            {
                "profile_id": user_id,
                "name": aadhaar_doc["name"],
                "mobile": pending.data["mobile"],
                "email": email,
                "dob": aadhaar_doc["dob"].isoformat() if hasattr(aadhaar_doc["dob"], "isoformat") else aadhaar_doc["dob"],
                "address": aadhaar_doc["address"],
                "aadhaar_number": pending.data["aadhaar_number"],
                "documents": documents,
                "verification_status": "verified",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    citizen_id = citizen_result.data[0]["id"]

    supabase_admin.table("pending_registrations").delete().eq("id", payload.pending_id).execute()

    access_token = create_access_token(user_id=user_id, role="citizen", citizen_id=citizen_id, email=email)
    refresh_token = create_refresh_token(user_id=user_id)

    await log_action(actor_id=user_id, action="registration_completed", target_citizen_id=citizen_id,
                      details={"pending_id": payload.pending_id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, citizen_id=citizen_id)


@router.post("/login-request-otp", response_model=OTPSentResponse)
async def login_request_otp(payload: LoginRequestOTP):
    citizen = (
        supabase_admin.table("citizens")
        .select("id, mobile")
        .eq("mobile", payload.mobile)
        .maybe_single()
        .execute()
    )
    if not citizen.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No citizen registered with this mobile number")

    otp = f"{random.randint(0, 999999):06d}"
    _OTP_STORE[payload.mobile] = {"otp": otp, "expires_at": datetime.now(timezone.utc).timestamp() + OTP_TTL_SECONDS}

    # Dev-mode: OTP is returned in the response instead of sent via real SMS.
    return OTPSentResponse(otp_sent=True, dev_otp=otp if settings.OTP_DEV_MODE else None)


@router.post("/login-verify-otp", response_model=OTPVerifyResponse)
async def login_verify_otp(payload: LoginVerifyOTP):
    entry = _OTP_STORE.get(payload.mobile)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No OTP was requested for this mobile number")
    if datetime.now(timezone.utc).timestamp() > entry["expires_at"]:
        del _OTP_STORE[payload.mobile]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired, please request a new one")
    if entry["otp"] != payload.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect OTP")

    del _OTP_STORE[payload.mobile]

    citizen = (
        supabase_admin.table("citizens")
        .select("id, profile_id")
        .eq("mobile", payload.mobile)
        .maybe_single()
        .execute()
    )
    if not citizen.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No citizen registered with this mobile number")

    user_id = citizen.data["profile_id"]
    citizen_id = citizen.data["id"]

    access_token = create_access_token(user_id=user_id, role="citizen", citizen_id=citizen_id)
    refresh_token = create_refresh_token(user_id=user_id)

    await log_action(actor_id=user_id, action="otp_login", target_citizen_id=citizen_id)

    return OTPVerifyResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/resend-otp", response_model=OTPSentResponse)
async def resend_otp(payload: ResendOTPRequest):
    mobile = payload.mobile
    if not mobile and payload.pending_id:
        pending = (
            supabase_admin.table("pending_registrations")
            .select("mobile")
            .eq("id", payload.pending_id)
            .maybe_single()
            .execute()
        )
        if pending.data:
            mobile = pending.data["mobile"]

    if not mobile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide either pending_id or mobile")

    otp = f"{random.randint(0, 999999):06d}"
    _OTP_STORE[mobile] = {"otp": otp, "expires_at": datetime.now(timezone.utc).timestamp() + OTP_TTL_SECONDS}
    return OTPSentResponse(otp_sent=True, dev_otp=otp if settings.OTP_DEV_MODE else None)


# ---------------------------------------------------------------------------
# Mock DigiLocker (simulated external system) — exposed as real HTTP endpoints
# too, in addition to being called internally by /auth/callback, so the
# frontend's consent screen can hit them directly if it wants to show the
# fetched documents before finalizing registration.
# ---------------------------------------------------------------------------

digilocker_router = APIRouter(prefix="/mock-digilocker", tags=["mock-digilocker"])


@digilocker_router.post("/token", response_model=DigilockerTokenResponse)
async def mock_digilocker_token(payload: DigilockerTokenRequest):
    try:
        result = await digilocker_mock.exchange_code_for_token(payload.code, payload.pending_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DigilockerTokenResponse(**result)


@digilocker_router.get("/issued-documents", response_model=DigilockerDocumentsResponse)
async def mock_digilocker_issued_documents(authorization: str = Header(default="")):
    # Bearer <mock_token> — mock token issued by /mock-digilocker/token above.
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing mock DigiLocker bearer token")
    mock_token = authorization.replace("Bearer ", "").strip()
    try:
        documents = await digilocker_mock.fetch_issued_documents(mock_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DigilockerDocumentsResponse(documents=documents)