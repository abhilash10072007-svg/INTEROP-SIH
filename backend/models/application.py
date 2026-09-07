"""Pydantic schemas for the service catalog, applications, official, and admin routers."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------- Service Catalog ----------

class ServiceSummary(BaseModel):
    workflow_id: str
    service_name: str
    description: Optional[str] = None
    steps_count: int


class ServicesListResponse(BaseModel):
    services: list[ServiceSummary]


class WorkflowStep(BaseModel):
    step_order: int
    step_name: str
    step_type: str
    auto_or_manual: str


class ServiceDetailResponse(BaseModel):
    workflow_id: str
    service_name: str
    steps: list[WorkflowStep]


# ---------- Applications ----------

class CreateApplicationRequest(BaseModel):
    workflow_id: str


class CreateApplicationResponse(BaseModel):
    application_id: str
    current_step: int
    status: str


class ApplicationSummary(BaseModel):
    application_id: str
    service_name: str
    status: str
    current_step: int
    updated_at: datetime


class ApplicationsListResponse(BaseModel):
    applications: list[ApplicationSummary]


class ApplicationDetailResponse(BaseModel):
    application_id: str
    workflow: dict
    current_step: int
    status: str
    step_history: list[dict]
    data_json: dict


class AdvanceStepRequest(BaseModel):
    step_order: int
    data: dict[str, Any] = {}


class AdvanceStepResponse(BaseModel):
    current_step: int
    status: str
    message: str


class UploadDocumentResponse(BaseModel):
    file_url: str
    ocr_result: Optional[dict] = None
    face_match_result: Optional[dict] = None


# ---------- Official Portal ----------

class OfficialQueueItem(BaseModel):
    application_id: str
    citizen_name: str
    service_name: str
    current_step: int
    submitted_at: datetime
    sla_deadline: Optional[datetime] = None
    risk_flags: list[str] = []


class OfficialQueueResponse(BaseModel):
    applications: list[OfficialQueueItem]


class OfficialApplicationDetailResponse(BaseModel):
    application_id: str
    workflow: dict
    current_step: int
    status: str
    step_history: list[dict]
    data_json: dict
    ml_scores: dict
    citizen_profile: dict


class ReviewDecisionRequest(BaseModel):
    action: str  # "approve" | "reject" | "request_info"
    notes: Optional[str] = None


class ReviewDecisionResponse(BaseModel):
    status: str
    message: str


# ---------- Admin Portal ----------

class DataQualityFlag(BaseModel):
    citizen_id: str
    issue_type: str  # "low_fuzzy_match" | "ocr_tamper_flag" | "fraud_flag"
    confidence_score: Optional[float] = None
    flagged_at: datetime


class DataQualityFlagsResponse(BaseModel):
    flags: list[DataQualityFlag]


class AdminUser(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime


class AdminUsersResponse(BaseModel):
    users: list[AdminUser]


class UpdateUserRoleRequest(BaseModel):
    role: str


class AnalyticsResponse(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    by_service: dict[str, int]
    avg_processing_time_days: float
    sla_breach_count: int
    ml_auto_approved_count: int
    manual_review_count: int
    applications_over_time: list[dict]