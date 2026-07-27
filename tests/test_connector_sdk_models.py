from __future__ import annotations

import pytest

from erpguard.connectors.sdk.models import (
    CapabilityDefinition,
    ConnectorFeatures,
    ConnectorMetadata,
    ConnectorContext,
)


def test_connector_metadata_requires_plugin_identity_and_features():
    metadata = ConnectorMetadata(
        connector_id="fake",
        package_name="erpguard",
        version="0.1.0",
        display_name="Fake Connector",
        vendor="ERPGuard",
        system_types=["fake_erp"],
        supported_versions=["1"],
        plugin_api_version="2",
        features=ConnectorFeatures(),
    )
    assert metadata.connector_id == "fake"
    assert metadata.features.controlled_write is False


def test_connector_context_rejects_raw_secret_fields():
    with pytest.raises(ValueError, match="secret"):
        ConnectorContext(tenant_id="tenant-1", connection_id="conn-1", credentials={"api_key": "raw"})


def test_capability_definition_requires_canonical_name():
    with pytest.raises(ValueError):
        CapabilityDefinition(name="", version="1", safety_tier="read_only")
