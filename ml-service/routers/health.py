from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "GovConnect ML Microservice",
        "models_loaded": ["rapidfuzz", "risk_model.pkl", "fraud_model.pkl", "groq_client"]
    }