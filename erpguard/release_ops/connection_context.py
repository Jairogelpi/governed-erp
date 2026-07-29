from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import get_connection, get_latest_skill_version, get_skill
from erpguard.release_ops.models import ConnectionContextModel


class ConnectionContextService:
    def __init__(self, session) -> None:
        self.session = session

    def resolve(self, skill_id: str) -> ConnectionContextModel:
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' not found.")

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"No skill version found for skill '{skill_id}'.")

        try:
            pkg = json.loads(version_row.skill_package_json)
        except Exception:
            pkg = {}

        connection_id = pkg.get("connection_id")
        if not connection_id:
            return ConnectionContextModel(
                connection_id="",
                skill_id=skill_id,
                erp_type="unknown",
                connection_status="missing",
                url="",
                database="",
                username="",
                has_credentials=False,
                secrets_redacted=True,
                resolved=False,
                missing_reason="missing_connection_context: skill package has no connection_id",
            )

        conn_row = get_connection(self.session, connection_id)
        if conn_row is None:
            return ConnectionContextModel(
                connection_id=connection_id,
                skill_id=skill_id,
                erp_type="unknown",
                connection_status="missing",
                url="",
                database="",
                username="",
                has_credentials=False,
                secrets_redacted=True,
                resolved=False,
                missing_reason=f"missing_connection_context: connection '{connection_id}' not found",
            )

        try:
            config = json.loads(conn_row.config_json)
        except Exception:
            config = {}

        return ConnectionContextModel(
            connection_id=connection_id,
            skill_id=skill_id,
            erp_type=conn_row.erp_type,
            connection_status=conn_row.status,
            url=config.get("url", ""),
            database=config.get("database", ""),
            username=config.get("username", ""),
            has_credentials="api_key" in config,
            secrets_redacted=True,
            resolved=True,
            missing_reason=None,
        )

    def resolve_config(self, skill_id: str) -> tuple[dict, str]:
        """Returns (full config dict, connection_id) — used internally by the runtime."""
        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"No skill version for '{skill_id}'.")

        try:
            pkg = json.loads(version_row.skill_package_json)
        except Exception:
            pkg = {}

        connection_id = pkg.get("connection_id", "")
        if not connection_id:
            raise ValueError(f"missing_connection_context: skill '{skill_id}' has no connection_id in package.")

        conn_row = get_connection(self.session, connection_id)
        if conn_row is None:
            raise ObjectNotFoundError(f"missing_connection_context: connection '{connection_id}' not found.")

        try:
            config = json.loads(conn_row.config_json)
        except Exception:
            config = {}

        return config, connection_id
