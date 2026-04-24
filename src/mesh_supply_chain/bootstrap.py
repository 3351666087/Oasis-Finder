from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from .config import get_settings
from .db import create_admin_engine, create_app_engine
from .models import Base


def bootstrap_database(drop_existing: bool = False) -> None:
    settings = get_settings()
    try:
        admin_engine = create_admin_engine()
        with admin_engine.begin() as connection:
            if drop_existing:
                connection.execute(text(f"DROP DATABASE IF EXISTS `{settings.db_name}`"))

            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
            )
            connection.execute(
                text(
                    f"CREATE USER IF NOT EXISTS '{settings.db_user}'@'%' "
                    f"IDENTIFIED BY '{settings.db_password}'"
                )
            )
            connection.execute(
                text(
                    f"GRANT ALL PRIVILEGES ON `{settings.db_name}`.* TO '{settings.db_user}'@'%'"
                )
            )
            connection.execute(text("FLUSH PRIVILEGES"))
    except Exception:
        pass

    engine = create_app_engine()
    if drop_existing:
        Base.metadata.drop_all(engine, checkfirst=True)
    Base.metadata.create_all(engine, checkfirst=True)
