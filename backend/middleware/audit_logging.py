"""
Lightweight ASGI middleware that records every mutating request (POST/PUT/
DELETE/PATCH) at the transport level, independent of whether the route handler
also calls `services.audit_service.log_action` for a richer, business-level
entry. This gives a coarse safety-net trail (method, path, status, actor if
present) even for routes that forget to log explicitly.
"""
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.supabase_client import supabase_admin

MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        if request.method in MUTATING_METHODS and not request.url.path.startswith("/health"):
            actor_id = None
            auth_header = request.headers.get("authorization", "")
            # Best-effort actor extraction; failures here must never affect the response.
            try:
                if auth_header.lower().startswith("bearer "):
                    from core.auth import decode_token  # local import avoids circular import at module load

                    payload = decode_token(auth_header.split(" ", 1)[1])
                    actor_id = payload.get("sub")
            except Exception:  # noqa: BLE001
                pass

            try:
                supabase_admin.table("audit_logs").insert(
                    {
                        "actor_id": actor_id,
                        "action": f"{request.method} {request.url.path}",
                        "target_citizen_id": None,
                        "details": {"status_code": response.status_code, "duration_ms": duration_ms},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ).execute()
            except Exception as exc:  # noqa: BLE001
                print(f"[audit_logging middleware] failed to log request: {exc}")

        return response