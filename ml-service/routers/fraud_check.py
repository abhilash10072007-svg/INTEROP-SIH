from fastapi import APIRouter
from pydantic import BaseModel
import joblib
import numpy as np

router = APIRouter(prefix="/ml", tags=["Fraud Check"])

class FraudMetadata(BaseModel):
    submission_time_gap_seconds: float
    similar_recent_applications: int
    device_change_flag: bool

class FraudRequest(BaseModel):
    citizen_id: str
    application_metadata: FraudMetadata

fraud_model = joblib.load("models/fraud_model.pkl")

@router.post("/fraud-check")
def fraud_check(req: FraudRequest):
    meta = req.application_metadata
    features = np.array([[meta.submission_time_gap_seconds, meta.similar_recent_applications, int(meta.device_change_flag)]])
    score = float(-fraud_model.decision_function(features)[0])
    is_anomaly = fraud_model.predict(features)[0] == -1

    reasons = []
    if meta.submission_time_gap_seconds < 20:
        reasons.append("unusually fast resubmission")
    if meta.similar_recent_applications > 2:
        reasons.append("multiple similar recent applications")
    if meta.device_change_flag:
        reasons.append("sudden device switch")

    return {
        "anomaly_score": round(min(max(score + 0.5, 0.0), 1.0), 2),
        "flagged": is_anomaly or len(reasons) > 0,
        "reasons": reasons if len(reasons) > 0 else ["standard application pattern"]
    }