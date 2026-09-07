"""
Mock DigiLocker service.

Simulates the external DigiLocker OAuth + document-issuance flow so the rest
of the system can be built without real government API access. Backed by the
`mock_gov_*` tables seeded by the database team (Aadhaar/PAN/Voter/Udyam).

Flow:
1. Frontend redirects citizen through a fake "DigiLocker consent" screen and
   gets back a `code`.
2. Backend calls `exchange_code_for_token(code, pending_id)` -> mock access token.
3. Backend calls `fetch_issued_documents(mock_token)` -> list of documents,
   looked up from the pending registration's Aadhaar number against the
   seeded mock government tables.
"""
import secrets
from datetime import date
from typing import Any

from core.supabase_client import supabase_admin

# In-memory store of mock tokens issued during this process's lifetime.
# Fine for a hackathon demo; would be Redis/DB-backed in production.
_MOCK_TOKENS: dict[str, dict[str, Any]] = {}

MOCK_TOKEN_TTL_SECONDS = 600


def generate_mock_code(pending_id: str) -> str:
    """Used when simulating the redirect step (not exposed as an endpoint, but
    useful for seeding a believable `code` if the frontend needs one)."""
    return secrets.token_urlsafe(16)


async def exchange_code_for_token(code: str, pending_id: str) -> dict[str, Any]:
    """POST /mock-digilocker/token equivalent, called internally by /auth/callback."""
    pending = (
        supabase_admin.table("pending_registrations")
        .select("*")
        .eq("id", pending_id)
        .maybe_single()
        .execute()
    )
    if not pending.data:
        raise ValueError("Unknown pending_id")

    token = f"mock_token_{secrets.token_hex(12)}"
    _MOCK_TOKENS[token] = {
        "pending_id": pending_id,
        "aadhaar_number": pending.data["aadhaar_number"],
    }
    return {"access_token": token, "expires_in": MOCK_TOKEN_TTL_SECONDS}


async def fetch_issued_documents(mock_token: str) -> list[dict[str, Any]]:
    """GET /mock-digilocker/issued-documents equivalent.

    Looks up the citizen's Aadhaar number in mock_gov_uidai, then pulls
    matching PAN/Voter/Udyam records (if any) so the fuzzy-matcher has
    something to compare against.
    """
    token_data = _MOCK_TOKENS.get(mock_token)
    if not token_data:
        raise ValueError("Invalid or expired mock DigiLocker token")

    aadhaar_number = token_data["aadhaar_number"]

    uidai = (
        supabase_admin.table("mock_gov_uidai")
        .select("*")
        .eq("aadhaar_number", aadhaar_number)
        .maybe_single()
        .execute()
    )
    if not uidai.data:
        raise ValueError("No matching Aadhaar record found in mock UIDAI database")

    documents: list[dict[str, Any]] = [
        {
            "doc_type": "aadhaar",
            "doc_number_masked": f"XXXX-XXXX-{aadhaar_number[-4:]}",
            "name": uidai.data["name"],
            "dob": uidai.data["dob"],
            "address": uidai.data["address"],
        }
    ]

    pan = (
        supabase_admin.table("mock_gov_pan")
        .select("*")
        .eq("aadhaar_number", aadhaar_number)
        .maybe_single()
        .execute()
    )
    if pan.data:
        documents.append(
            {
                "doc_type": "pan",
                "doc_number": pan.data["pan_number"],
                "name": pan.data["name"],
                "dob": pan.data["dob"],
                "address": pan.data.get("address", uidai.data["address"]),
            }
        )

    voter = (
        supabase_admin.table("mock_gov_voter")
        .select("*")
        .eq("aadhaar_number", aadhaar_number)
        .maybe_single()
        .execute()
    )
    if voter.data:
        documents.append(
            {
                "doc_type": "voter_id",
                "doc_number": voter.data["voter_id"],
                "name": voter.data["name"],
                "dob": voter.data["dob"],
                "address": voter.data.get("address", uidai.data["address"]),
            }
        )

    udyam = (
        supabase_admin.table("mock_gov_udyam")
        .select("*")
        .eq("aadhaar_number", aadhaar_number)
        .maybe_single()
        .execute()
    )
    if udyam.data:
        documents.append(
            {
                "doc_type": "udyam",
                "doc_number": udyam.data["udyam_number"],
                "name": udyam.data["name"],
                "dob": udyam.data.get("dob", uidai.data["dob"]),
                "address": udyam.data.get("address", uidai.data["address"]),
            }
        )

    return documents


async def lookup_gov_record(document_type: str, document_number: str) -> dict[str, Any] | None:
    """Used by /citizen/link-records to look up a single record by type + number."""
    table_map = {
        "pan": ("mock_gov_pan", "pan_number"),
        "voter_id": ("mock_gov_voter", "voter_id"),
        "udyam": ("mock_gov_udyam", "udyam_number"),
    }
    if document_type not in table_map:
        raise ValueError(f"Unsupported document_type '{document_type}'")

    table, column = table_map[document_type]
    result = (
        supabase_admin.table(table)
        .select("*")
        .eq(column, document_number)
        .maybe_single()
        .execute()
    )
    return result.data