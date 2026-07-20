"""
Entry point for the Documentation Generator & Sync Agent API.

Run locally with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app.api.routes import webhook, repos
from app.core.config import settings

app = FastAPI(
    title="Doc Sync Agent",
    description="Generates and syncs documentation from code changes.",
    version="0.1.0",
)

# Each router owns one concern: webhook = ingestion, repos = dashboard/API for status.
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])


@app.get("/health")
def health_check():
    """Simple liveness check so Railway/uptime monitors have something to hit."""
    return {"status": "ok", "env": settings.ENVIRONMENT}
