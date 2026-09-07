from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/ml", tags=["Scheme Recommend"])

class SchemeReq(BaseModel):
    age: int
    income_band: str
    category: str
    business_type: str

MOCK_SCHEMES = [
    {"name": "PM SVANidhi", "max_age": 65, "incomes": ["low"], "businesses": ["street_vendor", "food_cart", "retail"]},
    {"name": "PMEGP Subsidy", "max_age": 55, "incomes": ["low", "medium"], "businesses": ["manufacturing", "services", "food_cart"]},
    {"name": "Mudra Shishu Scheme", "max_age": 60, "incomes": ["low", "medium"], "businesses": ["retail", "artisan", "services"]}
]

@router.post("/scheme-recommend")
def recommend_schemes(req: SchemeReq):
    results = []
    for s in MOCK_SCHEMES:
        score = 0.5
        if req.age <= s["max_age"]: score += 0.2
        if req.income_band in s["incomes"]: score += 0.2
        if req.business_type in s["businesses"]: score += 0.1
        results.append({"scheme_name": s["name"], "match_score": round(min(score, 0.98), 2)})
    
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {"recommended_schemes": results}