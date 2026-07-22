"""
Manually triggers process_push_event with a real webhook-shaped payload,
without needing an actual GitHub webhook or a running Celery worker.
Celery tasks are still plain functions underneath — calling them directly
(instead of .delay()) just runs the task body synchronously, in-process.

This resolves old_ref/new_ref against your LOCAL repo (since it has full
history) to get real commit SHAs, then builds the payload exactly like
GitHub would send it. process_push_event itself clones the repo fresh
from GitHub into REPO_CLONE_DIR — so your local repo is only used here to
look up which SHAs to test with, not as the source of truth for the diff.

Usage:
    python -m scripts.test_webhook <github_owner/repo> [--old-ref HEAD~1] [--new-ref HEAD]

Example:
    python -m scripts.test_webhook Joprax/AutoDoc-sync-agent
"""
import argparse
import subprocess

from app.workers.tasks import process_push_event


def _resolve_sha(ref: str) -> str:
    result = subprocess.run(["git", "rev-parse", ref], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not resolve '{ref}' in the current repo: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("github_full_name", help='e.g. "Joprax/AutoDoc-sync-agent"')
    parser.add_argument("--old-ref", default="HEAD~1")
    parser.add_argument("--new-ref", default="HEAD")
    args = parser.parse_args()

    old_sha = _resolve_sha(args.old_ref)
    new_sha = _resolve_sha(args.new_ref)

    payload = {
        "repository": {
            "full_name": args.github_full_name,
            "clone_url": f"https://github.com/{args.github_full_name}.git",
        },
        "before": old_sha,
        "after": new_sha,
    }

    print(f"Simulating push for {args.github_full_name}: {old_sha[:8]} -> {new_sha[:8]}\n")

    # Calling the task function directly — no .delay(), no worker, runs inline.
    result = process_push_event(payload)
    print("\nResult:", result)

    if result.get("status") == "failed":
        from app.db.base import SessionLocal
        from app.db.models import SyncRun

        db = SessionLocal()
        try:
            run = db.query(SyncRun).filter(SyncRun.id == result["sync_run_id"]).first()
            print("Error detail:", run.error_message if run else "(sync run not found)")
        finally:
            db.close()


if __name__ == "__main__":
    main()