from fastapi import APIRouter
from pydantic import BaseModel
import joblib
import numpy as np

router = APIRouter(prefix="/ml", tags=["Risk Score"])

class RiskRequest(BaseModel):
    age: int
    income: float
    existing_loans: int
    avg_monthly_txn: float
    txn_stability_score: float
    business_type: str = "retail"

risk_model = joblib.load("models/risk_model.pkl")

@router.post("/risk-score")
def predict_risk(req: RiskRequest):
    features = np.array([[req.age, req.income, req.existing_loans, req.avg_monthly_txn, req.txn_stability_score]])
    prob = float(risk_model.predict_proba(features)[0][1])
    
    if prob < 0.30:
        cat, rec = "low", "auto_approve"
    elif prob < 0.60:
        cat, rec = "medium", "manual_review"
    else:
        cat, rec = "high", "reject"

    return {
        "risk_score": round(prob, 2),
        "risk_category": cat,
        "recommendation": rec
    }