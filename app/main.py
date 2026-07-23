"""
Entry point for the Documentation Generator & Sync Agent API.

Run locally with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import webhook, repos
from app.core.config import settings

app = FastAPI(
    title="Doc Sync Agent",
    description="Generates and syncs documentation from code changes.",
    version="0.1.0",
)

# Dashboard runs on a different origin than the API — browsers block
# cross-origin requests by default, so this explicitly allows the dashboard
# through. localhost:3000 covers local dev; DASHBOARD_URL (set in
# production) covers the deployed Vercel URL. Kept as an explicit allowlist
# rather than "*", since this API also handles webhook secrets.
allowed_origins = ["http://localhost:3000"]
if settings.DASHBOARD_URL:
    allowed_origins.append(settings.DASHBOARD_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)
# Each router owns one concern: webhook = ingestion, repos = dashboard/API for status.
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])


@app.get("/health")
def health_check():
    """Simple liveness check so Railway/uptime monitors have something to hit."""
    return {"status": "ok", "env": settings.ENVIRONMENT}
