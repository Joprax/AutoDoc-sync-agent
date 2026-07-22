"""
Background tasks. process_push_event is the entry point for the whole
pipeline: clone/update the repo, diff the two commits, generate docs for
what changed, and persist the results.

Reuses the parse/diff/generate logic from prototype/ as-is rather than
duplicating it inside app/ — that logic was proven against real repos in
the standalone prototype, so this just wires it into the real trigger path.
Write-back to the repo (commit + open a PR) is still a TODO — this task
generates and stores docs but doesn't push anything anywhere yet.
"""
import sys
from pathlib import Path

# prototype/ lives at the project root, sibling to app/ — add the root to
# sys.path so it's importable from here without moving/duplicating the code.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prototype.differ import diff_symbols  # noqa: E402
from prototype.doc_generator import generate_docs_for_symbols  # noqa: E402
from prototype.git_source import get_changed_file_versions  # noqa: E402
from prototype.symbol_extractor import extract_symbols  # noqa: E402

from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models import Repo, SyncRun, Symbol, utcnow
from app.workers.celery_app import celery_app
from app.workers.git_ops import ensure_local_clone


@celery_app.task(name="process_push_event")
def process_push_event(payload: dict):
    """
    payload is the raw GitHub push webhook body. Uses repository.full_name,
    repository.clone_url, before (previous head SHA), and after (new head SHA).
    """
    repo_full_name = payload.get("repository", {}).get("full_name")
    clone_url = payload.get("repository", {}).get("clone_url")
    before_sha = payload.get("before")
    after_sha = payload.get("after")

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.github_full_name == repo_full_name).first()
        if repo is None:
            # Repo isn't registered yet — nothing to do until it's added via the API/dashboard.
            return {"status": "skipped", "reason": "repo not registered"}

        sync_run = SyncRun(repo_id=repo.id, commit_sha=after_sha, status="running")
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)

        try:
            local_path = ensure_local_clone(clone_url, repo_full_name, settings.REPO_CLONE_DIR)
            file_versions = get_changed_file_versions(local_path, before_sha, after_sha)

            # (file_path, Symbol) pairs for everything that needs new/updated docs.
            changed = []
            for file_path, (old_source, new_source) in file_versions.items():
                old_symbols = extract_symbols(old_source) if old_source is not None else {}
                new_symbols = extract_symbols(new_source) if new_source is not None else {}
                diff = diff_symbols(old_symbols, new_symbols)

                changed.extend((file_path, sym) for sym in diff.added)
                changed.extend((file_path, new_sym) for _, new_sym in diff.modified)

            sync_run.symbols_changed = len(changed)

            if changed:
                generated_docs = generate_docs_for_symbols([sym for _, sym in changed])

                for file_path, sym in changed:
                    existing = (
                        db.query(Symbol)
                        .filter(
                            Symbol.repo_id == repo.id,
                            Symbol.file_path == file_path,
                            Symbol.symbol_name == sym.qualified_name,
                        )
                        .first()
                    )
                    if existing is None:
                        existing = Symbol(
                            repo_id=repo.id,
                            file_path=file_path,
                            symbol_name=sym.qualified_name,
                        )
                        db.add(existing)

                    existing.signature_hash = sym.signature_hash
                    existing.last_doc_content = generated_docs.get(sym.qualified_name)
                    existing.last_synced_commit_sha = after_sha

            sync_run.status = "success"

            # TODO: write generated docs back to the repo — commit to a docs
            # branch off after_sha and open a PR, same review-friendly pattern
            # as the PR review agent, rather than pushing straight to main.

        except Exception as exc:  # noqa: BLE001 — top-level task boundary, log and record
            sync_run.status = "failed"
            sync_run.error_message = str(exc)
        finally:
            sync_run.finished_at = utcnow()
            db.commit()

        return {
            "status": sync_run.status,
            "sync_run_id": sync_run.id,
            "symbols_changed": sync_run.symbols_changed,
        }
    finally:
        db.close()