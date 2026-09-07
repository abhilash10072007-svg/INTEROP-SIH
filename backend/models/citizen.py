"""Pydantic schemas for auth, DigiLocker mock, and citizen profile endpoints."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Registration ----------

class PreRegisterRequest(BaseModel):
    full_name: str
    mobile: str = Field(..., min_length=10, max_length=15)
    email: EmailStr
    dob: date
    aadhaar_number: str = Field(..., min_length=12, max_length=12)


class PreRegisterResponse(BaseModel):
    pending_id: str


class AuthCallbackRequest(BaseModel):
    code: str
    pending_id: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    citizen_id: Optional[str] = None


class LoginRequestOTP(BaseModel):
    mobile: str


class LoginVerifyOTP(BaseModel):
    mobile: str
    otp: str


class OTPSentResponse(BaseModel):
    otp_sent: bool
    dev_otp: Optional[str] = None  # only populated when OTP_DEV_MODE is on


class ResendOTPRequest(BaseModel):
    pending_id: Optional[str] = None
    mobile: Optional[str] = None


class OTPVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str


# ---------- Mock DigiLocker ----------

class DigilockerTokenRequest(BaseModel):
    code: str
    pending_id: str


class DigilockerTokenResponse(BaseModel):
    access_token: str
    expires_in: int


class DigilockerDocument(BaseModel):
    doc_type: str
    doc_number: Optional[str] = None
    doc_number_masked: Optional[str] = None
    name: str
    dob: date
    address: str


class DigilockerDocumentsResponse(BaseModel):
    documents: list[DigilockerDocument]


# ---------- Citizen Profile ----------

class CitizenProfile(BaseModel):
    citizen_id: str
    name: str
    dob: date
    address: str
    linked_pan: Optional[str] = None
    linked_voter_id: Optional[str] = None
    linked_udyam: Optional[str] = None
    linked_license: Optional[str] = None
    verification_status: str


class CitizenProfileUpdate(BaseModel):
    address: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None


class LinkRecordsRequest(BaseModel):
    document_type: str  # "pan" | "voter_id" | "udyam" | "license"
    document_number: str


class LinkRecordsResponse(BaseModel):
    linked: bool
    confidence_score: float


class CitizenDocumentsResponse(BaseModel):
    documents: list[dict]