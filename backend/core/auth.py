"""
Auth core.

Two token sources both decode with the same Supabase JWT secret (HS256):
1. Tokens issued by real Supabase Auth (email/password flow used in /auth/callback
   after DigiLocker exchange) - these arrive as normal `access_token`s from
   supabase.auth.sign_up / sign_in.
2. Tokens we mint ourselves for the OTP login flow (/auth/login-verify-otp), shaped
   to match Supabase's claim structure so the same decode/guard logic works for both.

`role` lives in `profiles.role` and is embedded in the token's `app_metadata.role`
claim when we mint tokens; for real Supabase-issued tokens we look role up from the
`profiles` table on first decode and cache it on the request.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from core.config import settings
from core.supabase_client import supabase_admin

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h, fine for a hackathon demo


class AuthUser:
    """Lightweight representation of the authenticated caller."""

    def __init__(self, user_id: str, role: str, citizen_id: Optional[str] = None, email: Optional[str] = None):
        self.user_id = user_id
        self.role = role
        self.citizen_id = citizen_id
        self.email = email

    def __repr__(self) -> str:
        return f"AuthUser(user_id={self.user_id}, role={self.role}, citizen_id={self.citizen_id})"


def create_access_token(user_id: str, role: str, citizen_id: Optional[str] = None, email: Optional[str] = None) -> str:
    """Mint a Supabase-compatible JWT for the OTP login path."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": "authenticated",
        "email": email,
        "app_metadata": {"role": role, "citizen_id": citizen_id},
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "aud": "authenticated",
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=30),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience="authenticated",
            options={"verify_aud": True},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )


def _lookup_role_and_citizen(user_id: str) -> tuple[str, Optional[str]]:
    """Fallback lookup for tokens that don't carry app_metadata (real Supabase tokens)."""
    profile = (
        supabase_admin.table("profiles")
        .select("role")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    role = profile.data["role"] if profile.data else "citizen"

    citizen = (
        supabase_admin.table("citizens")
        .select("id")
        .eq("profile_id", user_id)
        .maybe_single()
        .execute()
    )
    citizen_id = citizen.data["id"] if citizen.data else None
    return role, citizen_id


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    app_meta = payload.get("app_metadata") or payload.get("user_metadata") or {}
    role = app_meta.get("role")
    citizen_id = app_meta.get("citizen_id")

    if role is None:
        role, citizen_id = _lookup_role_and_citizen(user_id)

    return AuthUser(user_id=user_id, role=role, citizen_id=citizen_id, email=payload.get("email"))


def require_roles(*allowed_roles: str):
    """Dependency factory: require the caller's role to be one of `allowed_roles`."""

    async def _guard(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles {allowed_roles}, got '{user.role}'",
            )
        return user

    return _guard


# Common shorthand guards used across routers
require_citizen = require_roles("citizen")
require_official = require_roles("official_rto", "official_bank")
require_admin = require_roles("admin")
require_official_or_admin = require_roles("official_rto", "official_bank", "admin")