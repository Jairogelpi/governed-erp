"""Alembic migration entry points for deployment and tests."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def upgrade_database(revision: str = "head") -> None:
    """Upgrade the configured database to the requested Alembic revision."""
    repository_root = Path(__file__).resolve().parents[2]
    config = Config(str(repository_root / "alembic.ini"))
    command.upgrade(config, revision)

