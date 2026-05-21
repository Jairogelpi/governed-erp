from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_demo_contains_marketplace_section_and_controls():
    html = client.get("/demo").text

    assert "Skill Marketplace / Connector Catalog" in html
    assert "marketplaceConnectorOutput" in html
    assert "marketplaceTemplateOutput" in html
    assert "marketplaceInstallOutput" in html
    assert "Install as draft" in html
    assert "Compile later" in html
    assert "/v1/marketplace/connectors" in html
    assert "/v1/marketplace/skill-templates" in html


def test_demo_marketplace_safety_copy_keeps_no_goals_visible():
    html = client.get("/demo").text

    assert "No MCP execution gateway" in html
    assert "No new ERP writes" in html
    assert "Templates install only as draft" in html
