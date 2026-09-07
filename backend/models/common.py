"""Shared/generic pydantic schemas used across multiple routers."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    ml_service_reachable: bool
    db_reachable: bool


class PaginationParams(BaseModel):
    limit: int = 20
    offset: int = 0


class AuditLogEntry(BaseModel):
    id: str
    actor_id: Optional[str] = None
    action: str
    target_citizen_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    timestamp: datetime


class NotificationOut(BaseModel):
    id: str
    message: str
    read_status: bool
    created_at: datetime