"""
Receives GitHub push/PR webhooks.

This endpoint does the minimum possible work: verify the request is really
from GitHub, then hand off to Celery and return immediately. Doing the
parse/generate work inline here would block the webhook and risk GitHub
timing out and retrying the delivery.
"""
import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.workers.tasks import process_push_event

router = APIRouter()


def verify_signature(payload_body: bytes, signature_header: str | None) -> None:
    """Raise 401 if the request wasn't signed with our shared webhook secret."""
    if signature_header is None:
        raise HTTPException(status_code=401, detail="Missing signature")

    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    body = await request.body()
    verify_signature(body, x_hub_signature_256)

    if x_github_event != "push":
        # We only care about pushes for now (PR-merge-to-main triggers a push too).
        return {"status": "ignored", "reason": f"event type {x_github_event} not handled"}

    payload = await request.json()

    # Hand off to Celery immediately — don't do parsing/LLM work in the request thread.
    process_push_event.delay(payload)

    return {"status": "queued"}
