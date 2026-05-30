"""UI tests for Sprint 78 - Odoo read evidence packs."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_odoo_read_evidence_pack_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read Evidence Packs" in response.content
    assert b"Sprint 78 creates evidence packs from existing Odoo read mappings" in response.content
    assert b"odooEvReadMappingId" in response.content
    assert b"odooEvEvidencePackId" in response.content
    assert b"odooEvCreate" in response.content
    assert b"odooEvAudit" in response.content
