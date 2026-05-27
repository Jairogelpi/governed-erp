from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ui_exposes_controlled_fake_erp_execution_section(client):
    html = client.get("/demo").text
    assert "Controlled Fake ERP Execution" in html
    assert "Sprint 48 runs only inside controlled Fake ERP." in html


def test_controlled_fake_erp_execution_fields_present(client):
    html = client.get("/demo").text
    for marker in (
        "fakeExecVersionId",
        "fakeExecDryRunId",
        "fakeExecTokenId",
        "fakeExecActorId",
        "fakeExecTarget",
        "fakeExecInputs",
        "fakeExecReason",
        "fakeExecOutput",
    ):
        assert marker in html


def test_controlled_fake_erp_execution_buttons_present(client):
    html = client.get("/demo").text
    assert "Run controlled Fake ERP execution" in html
    assert "Get Fake ERP execution result" in html
    assert "Fake ERP execution audit" in html
