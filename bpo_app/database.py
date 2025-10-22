from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import get_settings

engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


class Base(DeclarativeBase):
    pass


def init_engine(database_url: Optional[str] = None) -> Engine:
    global engine, SessionLocal

    settings = get_settings()
    url = database_url or settings.database_url
    parsed_url = make_url(url)

    connect_args = {"check_same_thread": False} if parsed_url.drivername.startswith("sqlite") else {}

    if parsed_url.drivername.startswith("sqlite") and parsed_url.database not in {None, "", ":memory:"}:
        db_path = Path(parsed_url.database)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    if engine is not None:
        engine.dispose()

    engine = create_engine(url, connect_args=connect_args, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


def get_sessionmaker() -> sessionmaker:
    global SessionLocal
    if SessionLocal is None:
        init_engine()
    assert SessionLocal is not None
    return SessionLocal


def get_db():
    session_factory = get_sessionmaker()
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()


init_engine()


__all__ = ["Base", "engine", "init_engine", "get_sessionmaker", "get_db", "SessionLocal"]
