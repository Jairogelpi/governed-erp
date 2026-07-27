from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, create_mock_engine, inspect, text

from erpguard.db.base import Base
import erpguard.db.model_packages  # noqa: F401
import erpguard.db.models  # noqa: F401
from erpguard.db.model_packages import ProcessDefinition


ROOT = Path(__file__).resolve().parents[1]


def _upgrade(url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    import os

    previous = os.environ.pop("ERPGUARD_DATABASE_URL", None)
    try:
        command.upgrade(config, "head")
    finally:
        if previous is not None:
            os.environ["ERPGUARD_DATABASE_URL"] = previous


def test_baseline_upgrade_preserves_existing_sqlite_data(tmp_path):
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO process_definitions "
                "(id, process_key, version, definition_json, created_at) "
                "VALUES ('p1', 'quote_to_order', '1.0.0', '{}', CURRENT_TIMESTAMP)"
            )
        )

    _upgrade(url)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM process_definitions")).scalar_one() == "p1"
    assert "alembic_version" in inspect(engine).get_table_names()


def test_fresh_sqlite_upgrade_creates_bounded_model_package_table(tmp_path):
    database = tmp_path / "fresh.db"
    url = f"sqlite:///{database.as_posix()}"
    _upgrade(url)

    engine = create_engine(url)
    tables = inspect(engine).get_table_names()
    assert "process_definitions" in tables
    assert ProcessDefinition.__module__ == "erpguard.db.model_packages.process"


def test_postgresql_metadata_can_be_compiled_without_network_access():
    statements: list[str] = []

    def executor(statement, *args, **kwargs):
        statements.append(str(statement))

    engine = create_mock_engine(
        "postgresql+psycopg://erpguard:password@localhost/erpguard",
        executor,
    )
    Base.metadata.create_all(bind=engine)
    assert any("process_definitions" in statement for statement in statements)
