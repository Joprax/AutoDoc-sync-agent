"""
Pydantic schemas — the shapes exposed over the API.
Kept separate from db/models.py so the API contract can evolve independently
of the database schema (e.g. hiding internal columns from the response).
"""
from datetime import datetime

from pydantic import BaseModel


class RepoOut(BaseModel):
    id: int
    github_full_name: str
    default_branch: str
    docs_output_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class SyncRunOut(BaseModel):
    id: int
    commit_sha: str
    status: str
    symbols_changed: int
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True
