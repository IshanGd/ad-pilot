"""Database engine, session factory, and ORM base.

Mirrors the schema in ``02_ARCHITECTURE.md`` / ``schema.sql``. On SQLite (local
dev) the tables are created from the ORM metadata on startup. On Postgres the
ORM columns are ``VARCHAR(36)`` while the real columns are ``UUID`` — close
enough for reads/writes but not for ``CREATE TABLE`` — so apply ``schema.sql``
once at deploy and ``init_db`` leaves Postgres alone.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def new_uuid() -> str:
    return str(uuid.uuid4())


def init_db() -> None:
    """Create tables on SQLite. On Postgres, schema.sql is the source of truth."""
    from app.models import tables  # noqa: F401  (register mappers)

    if _is_sqlite:
        Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
