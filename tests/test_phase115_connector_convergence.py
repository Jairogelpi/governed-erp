from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.app_factory import create_public_app
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.connectors.fake.plugin import FakeConnector
from erpguard.connectors.sdk.registry import ConnectorRegistry, discover_connectors
from erpguard.db.base import Base
from erpguard.db.model_packages.connections import UnifiedConnection
from erpguard.domain.connections.service import UnifiedConnectionService
from erpguard.infrastructure.secrets import EncryptedLocalSecretProvider


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_only_sdk_v2_entry_points_are_discoverable():
    registry = discover_connectors()
    assert [plugin.metadata.connector_id for plugin in registry.list()] == ["fake", "odoo"]
    assert all(plugin.metadata.plugin_api_version == "2" for plugin in registry.list())


def test_odoo_protocol_details_stay_inside_the_odoo_connector_package():
    connector_root = Path(__file__).parents[1] / "erpguard" / "connectors"
    odoo_terms = ("sale.order", "res.partner", "product.product", "XML-RPC", "JSON-2")

    violations = []
    for source_path in connector_root.rglob("*.py"):
        if "odoo" in source_path.parts:
            continue
        source = source_path.read_text(encoding="utf-8-sig")
        for term in odoo_terms:
            if term in source:
                violations.append(f"{source_path.relative_to(connector_root)}:{term}")

    assert violations == []


def test_unified_connection_is_validated_against_connector_definition():
    db = _session()
    provider = EncryptedLocalSecretProvider(Fernet.generate_key())
    service = UnifiedConnectionService(
        db,
        secret_provider=provider,
        connector_registry=ConnectorRegistry([FakeConnector()]),
    )

    with pytest.raises(ValueError, match="connector_not_found"):
        service.create(
            tenant_id="tenant-c2",
            created_by="user-c2",
            name="unknown",
            connector_type="calendar",
            endpoint="https://example.test",
            auth_type="api_key",
            secret="secret",
            metadata={},
        )


def test_runtime_flow_uses_tenant_connection_and_credential_reference_only():
    db = _session()
    connection_id = f"uconn_{uuid4().hex}"
    db.add(
        UnifiedConnection(
            id=connection_id,
            tenant_id="tenant-c2",
            name="Fake ERP",
            connector_type="fake",
            endpoint="fixture://fake-erp",
            auth_type="credential_ref",
            secret_ref="secret_ref_c2",
            metadata_json='{"environment":"test"}',
            status="active",
            created_by="user-c2",
        )
    )
    db.commit()

    service = ConnectorApplicationService(
        db,
        registry=ConnectorRegistry([FakeConnector()]),
    )
    connection, context = service.connection_context(
        tenant_id="tenant-c2",
        connection_id=connection_id,
        connector_id="fake",
    )
    assert connection.id == connection_id
    assert context.credential_ref == "secret_ref_c2"
    assert context.credentials == {}
    result = asyncio.run(
        service.test_connection(
            tenant_id="tenant-c2",
            connection_id=connection_id,
            connector_id="fake",
        )
    )
    assert result.status == "ok"
    assert result.safety_flags.raw_secret_accessed is False


def test_connector_runtime_context_rejects_cross_tenant_connection_access():
    db = _session()
    db.add(
        UnifiedConnection(
            id="uconn_tenant_c2",
            tenant_id="tenant-owner",
            name="Fake ERP",
            connector_type="fake",
            endpoint="fixture://fake-erp",
            auth_type="credential_ref",
            secret_ref="secret_ref_c2",
            metadata_json="{}",
            status="active",
            created_by="user-c2",
        )
    )
    db.commit()
    service = ConnectorApplicationService(db, registry=ConnectorRegistry([FakeConnector()]))

    with pytest.raises(ValueError, match="connection_not_found"):
        service.connection_context(
            tenant_id="tenant-other",
            connection_id="uconn_tenant_c2",
            connector_id="fake",
        )


def test_public_connector_routes_are_mounted_and_legacy_setup_is_not():
    client = TestClient(create_public_app(include_internal=False))

    assert client.get("/v1/connectors").status_code == 401
    assert client.get("/v1/connectors/fake").status_code == 401
    assert client.get("/v1/connector-setup/sessions").status_code == 404
    assert client.get("/v1/unified/connections").status_code == 404
