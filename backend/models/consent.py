"""Pydantic schemas for the consent management router."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConsentRequestCreate(BaseModel):
    citizen_id: str
    requested_by: str
    data_scope: str
    purpose: str


class ConsentRequestResponse(BaseModel):
    consent_id: str


class ConsentApproveRequest(BaseModel):
    consent_id: str
    approve: bool


class ConsentStatusResponse(BaseModel):
    status: str


class ConsentLogEntry(BaseModel):
    consent_id: str
    requested_by: str
    data_scope: str
    purpose: str
    status: str
    timestamp: datetime


class ConsentLogsResponse(BaseModel):
    logs: list[ConsentLogEntry]


class ConsentPendingResponse(BaseModel):
    pending_requests: list[ConsentLogEntry]