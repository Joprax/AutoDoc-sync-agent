"""
SQLAlchemy engine + session factory.

get_db() is a FastAPI dependency: it opens a session, hands it to the route,
then always closes it afterward (even if the route raises). This avoids
leaked connections under load.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
