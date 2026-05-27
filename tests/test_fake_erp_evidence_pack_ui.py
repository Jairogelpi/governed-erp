from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ui_exposes_fake_erp_evidence_pack_section(client):
    html = client.get("/demo").text
    assert "Persisted Fake ERP Evidence Pack" in html
    assert "Sprint 49 creates a persisted evidence pack from a completed Fake ERP execution." in html


def test_fake_erp_evidence_pack_fields_and_buttons_present(client):
    html = client.get("/demo").text
    for marker in ("fakePackExecutionId", "fakePackPackId", "fakePackOutput"):
        assert marker in html
    assert "Create Fake ERP evidence pack" in html
    assert "Get Fake ERP evidence pack" in html
    assert "Get latest execution evidence pack" in html
