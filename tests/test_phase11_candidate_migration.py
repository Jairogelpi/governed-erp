from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]


def _upgrade(url: str, revision: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, revision)


def test_candidate_integrity_migration_backfills_0007_rows(tmp_path):
    database = tmp_path / "candidate-0007.db"
    url = f"sqlite:///{database.as_posix()}"
    _upgrade(url, "0007_event_object_links")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO process_candidates "
                "(id, process_key, base_version, candidate_version, status, changes_json, "
                "evidence_json, created_by, created_at) "
                "VALUES ('legacy-candidate', 'quote_to_order', '1.0.0', '2.0.0', 'draft', "
                "'{}', '[]', 'legacy-user', CURRENT_TIMESTAMP)"
            )
        )
    _upgrade(url, "head")

    columns = {item["name"] for item in inspect(engine).get_columns("process_candidates")}
    assert {
        "tenant_id",
        "patch_json",
        "proposal_json",
        "base_definition_digest",
        "patch_digest",
        "candidate_definition_json",
        "candidate_definition_digest",
        "validation_status",
    } <= columns
    with engine.begin() as connection:
        legacy = connection.execute(
            text(
                "SELECT tenant_id, patch_json, validation_status "
                "FROM process_candidates WHERE id = 'legacy-candidate'"
            )
        ).mappings().one()
        assert legacy["tenant_id"] == "legacy"
        assert legacy["patch_json"] == '{}'
        assert legacy["validation_status"] == "legacy_unvalidated"

        connection.execute(
            text(
                "INSERT INTO process_candidates "
                "(id, tenant_id, process_key, base_version, candidate_version, status, patch_json, "
                "evidence_json, proposal_json, base_definition_digest, patch_digest, "
                "candidate_definition_json, candidate_definition_digest, validation_status, "
                "created_by, created_at) VALUES "
                "('tenant-a-candidate', 'tenant-a', 'quote_to_order', '1.0.0', '2.0.0', 'draft', "
                "'{}', '[]', '{}', '', '', '{}', '', 'valid', 'user-a', CURRENT_TIMESTAMP), "
                "('tenant-b-candidate', 'tenant-b', 'quote_to_order', '1.0.0', '2.0.0', 'draft', "
                "'{}', '[]', '{}', '', '', '{}', '', 'valid', 'user-b', CURRENT_TIMESTAMP)"
            )
        )
