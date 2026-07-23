"""
Registers a repo in the Repo table. process_push_event skips any webhook
for a repo it doesn't recognize, so a repo has to exist here before the
pipeline will do anything with it — this is the one-time setup step for that.

Also creates all tables if they don't exist yet, so this doubles as your
first-run DB setup — no separate migration step needed at this stage.

Usage:
    python -m scripts.seed_repo <github_owner/repo> [--branch main] [--docs-path docs/]

Example:
    python -m scripts.seed_repo Joprax/doc-sync-agent
"""
import argparse

from app.db.base import Base, SessionLocal, engine
from app.db.models import Repo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("github_full_name", help='e.g. "Joprax/doc-sync-agent"')
    parser.add_argument("--branch", default="main", help="Default branch (default: main)")
    parser.add_argument("--docs-path", default="docs/", help="Where docs live in the repo (default: docs/)")
    args = parser.parse_args()

    # Safe to call every time — only creates tables that don't already exist.
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        existing = db.query(Repo).filter(Repo.github_full_name == args.github_full_name).first()
        if existing:
            print(f"Already registered: {args.github_full_name} (id={existing.id})")
            return

        repo = Repo(
            github_full_name=args.github_full_name,
            default_branch=args.branch,
            docs_output_path=args.docs_path,
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        print(f"Registered: {repo.github_full_name} (id={repo.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
