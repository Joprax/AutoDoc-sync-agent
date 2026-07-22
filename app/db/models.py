"""
Core tables.

Repo          - a connected GitHub repo we watch.
Symbol        - one documented unit (function/class/endpoint) tracked over time.
                signature_hash lets us detect "did this actually change" without
                diffing full source text.
SyncRun       - one execution of the parse -> diff -> generate pipeline,
                so the dashboard can show history and status per push.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class Repo(Base):
    __tablename__ = "repos"

    id = Column(Integer, primary_key=True)
    github_full_name = Column(String, unique=True, nullable=False)  # e.g. "Joprax/pr-review-agent"
    default_branch = Column(String, default="main")
    docs_output_path = Column(String, default="docs/")
    created_at = Column(DateTime, default=utcnow)

    symbols = relationship("Symbol", back_populates="repo")
    sync_runs = relationship("SyncRun", back_populates="repo")


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False)
    file_path = Column(String, nullable=False)
    symbol_name = Column(String, nullable=False)      # e.g. "PRReviewer.run"
    signature_hash = Column(String, nullable=False)    # hash of params/types/decorators
    last_doc_content = Column(Text)
    last_synced_commit_sha = Column(String)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    repo = relationship("Repo", back_populates="symbols")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False)
    commit_sha = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | running | success | failed
    symbols_changed = Column(Integer, default=0)
    pr_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    repo = relationship("Repo", back_populates="sync_runs")
