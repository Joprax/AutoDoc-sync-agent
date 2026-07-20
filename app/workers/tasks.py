"""
Background tasks. process_push_event is the entry point for the whole
pipeline; right now it only records that a push happened. The parse/diff/
generate/write-back steps get filled in once the AST-diffing logic exists —
see the TODOs below for where each one plugs in.
"""
from app.db.base import SessionLocal
from app.db.models import Repo, SyncRun
from app.workers.celery_app import celery_app


@celery_app.task(name="process_push_event")
def process_push_event(payload: dict):
    """
    payload is the raw GitHub push webhook body. Expected fields we care
    about: repository.full_name, after (head commit sha), commits[].modified/added.
    """
    repo_full_name = payload.get("repository", {}).get("full_name")
    commit_sha = payload.get("after")

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.github_full_name == repo_full_name).first()
        if repo is None:
            # Repo isn't registered yet — nothing to do until it's added via the API/dashboard.
            return {"status": "skipped", "reason": "repo not registered"}

        sync_run = SyncRun(repo_id=repo.id, commit_sha=commit_sha, status="running")
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)

        try:
            # TODO 1: fetch the diff for `commit_sha` via the GitHub API
            # TODO 2: parse changed files into symbols (ast for Python, tree-sitter for JS/TS)
            # TODO 3: compare each symbol's signature_hash against app.db.models.Symbol
            #         to find what actually changed
            # TODO 4: for changed symbols, call Gemini to generate/update doc content
            # TODO 5: write results back (commit to a docs branch + open a PR)

            sync_run.status = "success"
            sync_run.symbols_changed = 0
        except Exception as exc:  # noqa: BLE001 — top-level task boundary, log and record
            sync_run.status = "failed"
            sync_run.error_message = str(exc)
        finally:
            from app.db.models import utcnow
            sync_run.finished_at = utcnow()
            db.commit()

        return {"status": sync_run.status, "sync_run_id": sync_run.id}
    finally:
        db.close()
