from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _html(client):
    return client.get("/demo").text


def test_ui_exposes_manual_dry_run_section(client):
    html = _html(client)
    assert "Manual Dry-Run Execution Record" in html
    assert "Sprint 47 creates a manual dry-run execution record only." in html


def test_manual_dry_run_fields_present(client):
    html = _html(client)
    for marker in (
        "manualDryRunVersionId",
        "manualDryRunTokenId",
        "manualDryRunActorId",
        "manualDryRunSourcePlanId",
        "manualDryRunSourceStepNumber",
        "manualDryRunMode",
        "manualDryRunInputs",
        "manualDryRunReason",
        "manualDryRunOutput",
    ):
        assert marker in html


def test_manual_dry_run_buttons_present(client):
    html = _html(client)
    assert "Create manual dry-run record" in html
    assert "Get dry-run result" in html
    assert "Dry-run audit" in html
