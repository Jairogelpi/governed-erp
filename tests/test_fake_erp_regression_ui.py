from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ui_exposes_manual_fake_erp_regression_suite_section(client):
    html = client.get("/demo").text
    assert "Manual Fake ERP Regression Suite" in html
    assert "Sprint 50 runs a manual regression case only inside controlled Fake ERP." in html


def test_manual_fake_erp_regression_fields_and_buttons_present(client):
    html = client.get("/demo").text
    for marker in (
        "fakeRegVersionId",
        "fakeRegDryRunId",
        "fakeRegCaseName",
        "fakeRegTarget",
        "fakeRegInputs",
        "fakeRegExpected",
        "fakeRegCaseId",
        "fakeRegTokenId",
        "fakeRegActorId",
        "fakeRegRunId",
        "fakeRegOutput",
        "Create regression case",
        "Run manual Fake ERP regression",
        "Regression audit",
    ):
        assert marker in html
