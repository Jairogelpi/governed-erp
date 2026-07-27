from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.db.models import Connection
from erpguard.infrastructure.secrets import EncryptedLocalSecretProvider


SECRET_KEYS = ("api_key", "password", "token", "secret")


def migrate_legacy_connections(
    session: Session,
    provider: EncryptedLocalSecretProvider,
) -> int:
    """Move legacy config secrets into encrypted storage and redact old rows."""
    migrated = 0
    for legacy in session.query(Connection).all():
        config = json.loads(legacy.config_json)
        secret_key = next((key for key in SECRET_KEYS if config.get(key)), None)
        if secret_key is None or config[secret_key] == "***REDACTED***":
            continue
        sealed = provider.seal(str(config[secret_key]))
        secret_id = f"secret_{uuid4().hex}"
        connection_id = f"uconn_legacy_{legacy.id}"
        if session.get(UnifiedConnection, connection_id) is not None:
            continue
        session.add(EncryptedSecret(
            id=secret_id,
            tenant_id="legacy",
            ciphertext=sealed.ciphertext,
            fingerprint=sealed.fingerprint,
            status="active",
        ))
        session.add(UnifiedConnection(
            id=connection_id,
            tenant_id="legacy",
            name=f"{legacy.name} ({legacy.id[-12:]})",
            connector_type=legacy.erp_type,
            endpoint=str(config.get("url", config.get("endpoint", ""))),
            auth_type=secret_key,
            secret_ref=secret_id,
            metadata_json=json.dumps({"legacy_connection_id": legacy.id}, sort_keys=True),
            status=legacy.status,
            created_by="legacy-migration",
        ))
        config[secret_key] = "***REDACTED***"
        legacy.config_json = json.dumps(config, sort_keys=True)
        migrated += 1
    session.commit()
    return migrated
