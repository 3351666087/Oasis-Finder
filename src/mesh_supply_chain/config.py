from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from sqlalchemy.engine import URL

ROOT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    project_root: Path = ROOT_DIR
    runtime_root: Path = ROOT_DIR / ".runtime"
    artifact_root: Path = ROOT_DIR / "artifacts"
    report_asset_root: Path = ROOT_DIR / "artifacts" / "report_assets"

    db_host: str = os.getenv("MESH_DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("MESH_DB_PORT", "3307"))
    db_name: str = os.getenv("MESH_DB_NAME", "mesh_supply_chain")
    db_user: str = os.getenv("MESH_DB_USER", "mesh_user")
    db_password: str = os.getenv("MESH_DB_PASSWORD", "MeshUser#2026")
    db_admin_user: str = os.getenv("MESH_DB_ADMIN_USER", "root")
    db_admin_password: str = os.getenv("MESH_DB_ADMIN_PASSWORD", "MeshRoot#2026")
    timezone: str = os.getenv("MESH_TIMEZONE", "Asia/Shanghai")
    db_connect_timeout_seconds: int = int(os.getenv("MESH_DB_CONNECT_TIMEOUT_SECONDS", "8"))
    db_pool_recycle_seconds: int = int(os.getenv("MESH_DB_POOL_RECYCLE_SECONDS", "1800"))

    @property
    def sqlalchemy_app_url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def sqlalchemy_admin_url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.db_admin_user,
            password=self.db_admin_password,
            host=self.db_host,
            port=self.db_port,
            database="mysql",
            query={"charset": "utf8mb4"},
        )

    def ensure_directories(self) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.report_asset_root.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
