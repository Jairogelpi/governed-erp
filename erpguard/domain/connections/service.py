from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.config import settings
from erpguard.connectors.sdk.registry import ConnectorRegistry, discover_connectors
from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.infrastructure.secrets import EncryptedLocalSecretProvider


class UnifiedConnectionService:
    def __init__(
        self,
        session: Session,
        *,
        secret_provider: EncryptedLocalSecretProvider | None = None,
        connector_registry: ConnectorRegistry | None = None,
    ):
        self.session = session
        self.secret_provider = secret_provider or EncryptedLocalSecretProvider(settings.local_secret_key)
        self.connector_registry = connector_registry or discover_connectors()

    def create(
        self,
        *,
        tenant_id: str,
        created_by: str,
        name: str,
        connector_type: str,
        endpoint: str,
        auth_type: str,
        secret: str,
        metadata: dict,
    ) -> UnifiedConnection:
        try:
            self.connector_registry.get(connector_type)
        except KeyError as exc:
            raise ValueError("connector_not_found") from exc
        sealed = self.secret_provider.seal(secret)
        secret_row = EncryptedSecret(
            id=f"secret_{uuid4().hex}",
            tenant_id=tenant_id,
            ciphertext=sealed.ciphertext,
            fingerprint=sealed.fingerprint,
            status="active",
        )
        connection = UnifiedConnection(
            id=f"uconn_{uuid4().hex}",
            tenant_id=tenant_id,
            name=name,
            connector_type=connector_type,
            endpoint=endpoint,
            auth_type=auth_type,
            secret_ref=secret_row.id,
            metadata_json=json.dumps(metadata, sort_keys=True),
            status="active",
            created_by=created_by,
        )
        self.session.add_all([secret_row, connection])
        self.session.commit()
        self.session.refresh(connection)
        return connection

    def list_for_tenant(self, tenant_id: str) -> list[UnifiedConnection]:
        return (
            self.session.query(UnifiedConnection)
            .filter(UnifiedConnection.tenant_id == tenant_id)
            .order_by(UnifiedConnection.created_at.desc())
            .all()
        )

    def get_for_tenant(self, connection_id: str, tenant_id: str) -> UnifiedConnection | None:
        return (
            self.session.query(UnifiedConnection)
            .filter(
                UnifiedConnection.id == connection_id,
                UnifiedConnection.tenant_id == tenant_id,
            )
            .one_or_none()
        )

