from __future__ import annotations

from erpguard.product.connector_catalog import ConnectorCatalogService


def test_connector_catalog_lists_odoo_as_implemented_and_placeholders_as_unavailable():
    connectors = ConnectorCatalogService().list_connectors()
    by_id = {connector.connector_id: connector for connector in connectors}

    assert by_id["odoo"].status == "implemented"
    assert by_id["odoo"].safe_modes == ["read_only", "dry_run", "r1_pilot", "r2_pilot"]
    assert by_id["gmail"].status == "placeholder"
    assert by_id["gmail"].execution_enabled is False
    assert by_id["whatsapp"].execution_enabled is False


def test_connector_detail_exposes_required_setup_and_safety_notes():
    connector = ConnectorCatalogService().get_connector("odoo")

    assert connector is not None
    assert "connection_id" in connector.required_config
    assert connector.safety_notes
    assert connector.real_execution_enabled is False


def test_missing_connector_returns_none():
    assert ConnectorCatalogService().get_connector("does_not_exist") is None
