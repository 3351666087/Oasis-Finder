from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings


def _engine_kwargs(echo: bool = False) -> dict:
    settings = get_settings()
    return {
        "future": True,
        "echo": echo,
        "pool_pre_ping": True,
        "pool_recycle": settings.db_pool_recycle_seconds,
        "connect_args": {"connect_timeout": settings.db_connect_timeout_seconds},
    }


def create_app_engine(echo: bool = False):
    settings = get_settings()
    return create_engine(settings.sqlalchemy_app_url, **_engine_kwargs(echo=echo))


def create_admin_engine(echo: bool = False):
    settings = get_settings()
    return create_engine(settings.sqlalchemy_admin_url, **_engine_kwargs(echo=echo))


SessionLocal = sessionmaker(bind=create_app_engine(), autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
