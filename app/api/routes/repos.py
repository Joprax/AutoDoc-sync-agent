"""
Read-oriented endpoints for the dashboard: list watched repos, and show
sync history/status per repo. Nothing here writes anything yet — that
happens through the webhook -> Celery pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Repo, SyncRun, Symbol
from app.schemas import RepoOut, SyncRunOut, SymbolOut

router = APIRouter()


@router.get("/", response_model=list[RepoOut])
def list_repos(db: Session = Depends(get_db)):
    return db.query(Repo).all()


@router.get("/{repo_id}/syncs", response_model=list[SyncRunOut])
def list_sync_runs(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if repo is None:
        raise HTTPException(status_code=404, detail="Repo not found")

    return (
        db.query(SyncRun)
        .filter(SyncRun.repo_id == repo_id)
        .order_by(SyncRun.created_at.desc())
        .all()
    )


@router.get("/{repo_id}/symbols", response_model=list[SymbolOut])
def list_symbols(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if repo is None:
        raise HTTPException(status_code=404, detail="Repo not found")

    return (
        db.query(Symbol)
        .filter(Symbol.repo_id == repo_id)
        .order_by(Symbol.file_path, Symbol.symbol_name)
        .all()
    )
