"""
Shared Supabase client instances.

- `supabase_admin` uses the service-role key: bypasses RLS, used for
  server-side writes (creating auth users, inserting citizens, audit logs...).
- `supabase_anon` uses the anon key: used for anything that should respect RLS
  (rare on the backend, but kept for completeness / OTP flows via Supabase Auth).
"""
from functools import lru_cache

from supabase import create_client, Client

from core.config import settings


@lru_cache
def get_admin_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@lru_cache
def get_anon_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# Convenience module-level singletons
supabase_admin: Client = get_admin_client()
supabase_anon: Client = get_anon_client()