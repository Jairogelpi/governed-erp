from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ui_exposes_erp_adapter_capability_registry_section(client):
    html = client.get("/demo").text
    assert "ERP Adapter Capability Registry" in html
    assert "Sprint 52 declares ERP adapter capabilities only." in html


def test_erp_adapter_capability_fields_and_buttons_present(client):
    html = client.get("/demo").text
    for marker in (
        "erpCapAdapterId",
        "erpCapOperationType",
        "erpCapObjectType",
        "erpCapRequestedFields",
        "erpCapOutput",
        "List ERP adapters",
        "Get adapter capabilities",
        "Check adapter capability",
    ):
        assert marker in html
