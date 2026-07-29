"""Exercise the C8.2 retired-schema migration against a real PostgreSQL
database. Skipped unless ERPGUARD_DATABASE_URL points at postgresql --
the CI postgres-migrations job sets this; local runs without it skip.

The sequence a plain `upgrade head` on a fresh database can't cover:
the 95 tables dropped by 0009 only exist on a database that was
already at 0008 with data in it. A fresh 0001_baseline never creates
them any more (Base.metadata no longer declares those ORM classes),
so this test rebuilds that pre-drop state via `downgrade 0008` (which
recreates the 95 tables, empty, from the migration's own column
definitions) before inserting rows and re-upgrading.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]

DATABASE_URL = os.environ.get("ERPGUARD_DATABASE_URL", "")
requires_postgres = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql"),
    reason="ERPGUARD_DATABASE_URL must point at a real PostgreSQL database",
)


def _config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@requires_postgres
def test_retired_tables_drop_on_reupgrade_while_live_tables_keep_their_rows():
    engine = create_engine(DATABASE_URL)
    config = _config(DATABASE_URL)

    # Clean slate: this job's database may carry state from a previous run.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    try:
        command.upgrade(config, "head")

        tables_at_head = set(inspect(engine).get_table_names())
        assert "oauth_states" not in tables_at_head
        assert "skills" in tables_at_head

        # Recreate the 95 retired tables (empty) by stepping back one revision.
        command.downgrade(config, "0008_candidate_integrity")
        tables_at_0008 = set(inspect(engine).get_table_names())
        assert "oauth_states" in tables_at_0008

        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO oauth_states "
                    "(id, state_token, profile_id, connector_id, redirect_uri, "
                    "scope_requested, status, created_at, expires_at) "
                    "VALUES ('oauth1', 'tok123', 'profile1', 'odoo', 'https://x', "
                    "'read', 'pending', now(), now())"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO skills (id, name, status, created_at, updated_at) "
                    "VALUES ('skill_c82_test', 'c82-live-table-check', 'draft', now(), now())"
                )
            )

        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM oauth_states")).scalar_one() == 1

        command.upgrade(config, "head")

        tables_after_reupgrade = set(inspect(engine).get_table_names())
        assert "oauth_states" not in tables_after_reupgrade

        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT status FROM skills WHERE id = 'skill_c82_test'")
            ).scalar_one()
            assert row == "draft"
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))


@requires_postgres
def test_downgrade_from_head_to_0008_is_non_fatal():
    engine = create_engine(DATABASE_URL)
    config = _config(DATABASE_URL)

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    try:
        command.upgrade(config, "head")
        command.downgrade(config, "0008_candidate_integrity")
        tables = set(inspect(engine).get_table_names())
        assert "oauth_states" in tables
        assert "write_impact_previews" in tables
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
