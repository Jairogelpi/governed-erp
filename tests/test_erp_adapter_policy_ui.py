from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ui_exposes_erp_adapter_safety_policy_section(client):
    html = client.get("/demo").text
    assert "ERP Adapter Safety Policy" in html
    assert "Sprint 53 evaluates ERP adapter safety policy only." in html


def test_erp_adapter_policy_fields_and_button_present(client):
    html = client.get("/demo").text
    for marker in (
        "erpPolicyAdapterId",
        "erpPolicyOperationType",
        "erpPolicyObjectType",
        "erpPolicyRequestedFields",
        "erpPolicyHasToken",
        "erpPolicyHasCredentials",
        "erpPolicyPhase",
        "erpPolicyOutput",
        "Check adapter policy",
    ):
        assert marker in html
