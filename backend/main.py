"""
GovConnect Backend — FastAPI entrypoint.

Run locally:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from middleware.audit_logging import AuditLoggingMiddleware
from routers import admin, applications, citizen, consent, health, notifications, official, services
from routers.auth import router as auth_router
from routers.auth import digilocker_router

app = FastAPI(
    title="GovConnect Backend",
    description="Unified citizen services backend — auth, applications, consent, official/admin portals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditLoggingMiddleware)

app.include_router(auth_router)
app.include_router(digilocker_router)
app.include_router(citizen.router)
app.include_router(services.router)
app.include_router(applications.router)
app.include_router(consent.router)
app.include_router(official.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(health.router)


@app.get("/", tags=["health"])
async def root():
    return {"service": "GovConnect Backend", "status": "running", "env": settings.ENV}