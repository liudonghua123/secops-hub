"""Database setup: SQLite + SQLAlchemy 2.0."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = os.environ.get(
    "SECOPS_DB", os.path.join(os.path.dirname(__file__), "..", "secops.db")
)

engine = create_engine(
    f"sqlite:///{os.path.abspath(DB_PATH)}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
