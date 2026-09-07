from fastapi import APIRouter
from pydantic import BaseModel
from rapidfuzz import fuzz

router = APIRouter(prefix="/ml", tags=["Fuzzy Match"])

class FuzzyMatchRequest(BaseModel):
    name1: str
    address1: str
    name2: str
    address2: str

@router.post("/fuzzy-match")
def fuzzy_match(req: FuzzyMatchRequest):
    name_sim = round(fuzz.token_sort_ratio(req.name1, req.name2) / 100.0, 2)
    addr_sim = round(fuzz.token_set_ratio(req.address1, req.address2) / 100.0, 2)
    overall = round((name_sim * 0.6) + (addr_sim * 0.4), 2)
    return {
        "name_similarity": name_sim,
        "address_similarity": addr_sim,
        "overall_confidence": overall,
        "is_likely_match": overall >= 0.70
    }