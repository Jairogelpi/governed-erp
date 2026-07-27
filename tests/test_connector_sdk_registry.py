from __future__ import annotations

from erpguard.connectors.sdk.registry import ConnectorRegistry, discover_connectors


def test_fake_connector_is_discovered_from_entry_point():
    registry = discover_connectors()
    fake = registry.get("fake")
    assert fake.metadata.connector_id == "fake"
    assert fake.metadata.features.object_read is True


def test_unknown_connector_is_rejected():
    registry = ConnectorRegistry([])
    try:
        registry.get("missing")
    except KeyError as exc:
        assert exc.args[0] == "missing"
    else:
        raise AssertionError("unknown connector was accepted")
