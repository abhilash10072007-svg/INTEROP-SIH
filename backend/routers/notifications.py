"""
Notifications router.
GET /notifications
PUT /notifications/{notification_id}/read

Note: most notification reads happen via Supabase Realtime directly from the
frontend (supabase.channel('notifications')...), these REST endpoints exist
for initial page-load fetches and mark-as-read.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import AuthUser, require_citizen
from core.supabase_client import supabase_admin
from models.common import MessageResponse, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(unread_only: bool = Query(False), user: AuthUser = Depends(require_citizen)):
    query = supabase_admin.table("notifications").select("*").eq("citizen_id", user.citizen_id).order("created_at", desc=True)
    if unread_only:
        query = query.eq("read_status", False)
    result = query.execute()
    return result.data or []


@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(notification_id: str, user: AuthUser = Depends(require_citizen)):
    existing = (
        supabase_admin.table("notifications")
        .select("citizen_id")
        .eq("id", notification_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if existing.data["citizen_id"] != user.citizen_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This notification does not belong to you")

    supabase_admin.table("notifications").update({"read_status": True}).eq("id", notification_id).execute()
    return MessageResponse(status="ok", message="Notification marked as read.")