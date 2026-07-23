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

from dotenv import load_dotenv

load_dotenv()  # must run before importing prototype.* — doc_generator.py reads
                # GEMINI_MODEL at import time (module-level), so if this runs
                # after that import, it's already too late and falls back to
                # the hardcoded default.

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
from app.workers.doc_writer import write_doc_pages
from app.workers.git_ops import ensure_local_clone
from app.workers.github_pr import checkout_new_branch, write_back_docs


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
    pushed_ref = payload.get("ref", "")  # e.g. "refs/heads/main"

    ZERO_SHA = "0" * 40  # GitHub's marker for "this ref didn't exist before this push"
                          # (branch creation) or "doesn't exist after" (branch deletion)

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.github_full_name == repo_full_name).first()
        if repo is None:
            # Repo isn't registered yet — nothing to do until it's added via the API/dashboard.
            return {"status": "skipped", "reason": "repo not registered"}

        # Only react to pushes on the repo's actual default branch. Without
        # this, the agent's own write-back (pushing a docs-sync/* branch to
        # open a PR) triggers a second webhook for THAT push, which then
        # tries to process itself — and fails, since a brand-new branch has
        # no meaningful "before" commit to diff against (before_sha is the
        # zero-SHA in that case).
        expected_ref = f"refs/heads/{repo.default_branch}"
        if pushed_ref != expected_ref:
            return {"status": "skipped", "reason": f"push to {pushed_ref!r}, not default branch"}

        if before_sha == ZERO_SHA or after_sha == ZERO_SHA:
            # Defense in depth — shouldn't reach here given the branch check
            # above, but a zero-SHA means there's no real diff to compute.
            return {"status": "skipped", "reason": "branch created or deleted, nothing to diff"}

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

            # Write generated docs back to the repo as a PR — only if we
            # actually generated something and a token is configured. No
            # token configured is a valid state during early development
            # (everything up to here still works and gets persisted), so
            # we skip write-back quietly rather than failing the whole run.
            if changed and settings.GITHUB_APP_TOKEN:
                branch_name = f"docs-sync/{after_sha[:7]}"
                checkout_new_branch(local_path, branch_name, after_sha)  # must happen before any docs are written

                relative_paths = write_doc_pages(
                    local_repo_path=local_path,
                    docs_output_path=repo.docs_output_path,
                    changed=changed,
                    generated_docs=generated_docs,
                )
                pr_url = write_back_docs(
                    local_repo_path=local_path,
                    repo_full_name=repo_full_name,
                    base_branch=repo.default_branch,
                    branch_name=branch_name,
                    base_sha=after_sha,
                    relative_paths=relative_paths,
                    symbols_changed=len(changed),
                    github_token=settings.GITHUB_APP_TOKEN,
                )
                sync_run.pr_url = pr_url

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