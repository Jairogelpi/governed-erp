"""Sprint 7 — API integration tests for write readiness & risk certification."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


class FakeOdooClient:
    def version(self):
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        return 2

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model" and domain == [
            [
                "model",
                "in",
                [
                    "res.users",
                    "ir.module.module",
                    "ir.model",
                    "ir.model.fields",
                    "sale.order",
                    "sale.order.line",
                    "product.product",
                    "product.template",
                    "res.partner",
                    "stock.quant",
                    "stock.move",
                    "stock.picking",
                    "mrp.production",
                    "mrp.bom",
                    "account.move",
                ],
            ]
        ]:
            return [{"model": m} for m in ["res.users", "sale.order", "product.product"]]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]:
            return []
        if model == "sale.order":
            return [
                {
                    "id": 42,
                    "name": "S00042",
                    "state": "sale",
                    "order_line": [90],
                    "amount_total": 500.0,
                }
            ]
        if model == "sale.order.line":
            return [
                {"id": 90, "product_id": [15, "P 100ML"], "product_uom_qty": 10, "price_unit": 12.3}
            ]
        if model == "product.product":
            return [
                {
                    "id": 15,
                    "display_name": "P 100ML",
                    "default_code": "P100",
                    "tracking": "none",
                    "standard_price": 9.0,
                }
            ]
        return []

    def fields_get(self, model, attributes=None):
        if model == "sale.order":
            return {"id": {}, "name": {}, "state": {}, "order_line": {}, "amount_total": {}}
        if model == "sale.order.line":
            return {
                "id": {},
                "order_id": {},
                "product_id": {},
                "product_uom_qty": {},
                "price_unit": {},
                "price_subtotal": {},
            }
        if model == "product.product":
            return {
                "id": {},
                "display_name": {},
                "default_code": {},
                "tracking": {},
                "standard_price": {},
            }
        if model == "product.template":
            return {"id": {}, "display_name": {}, "default_code": {}}
        return {}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 2
        if model == "product.product":
            return 1
        return 0


_OPERATOR = {"type": "user", "id": "op1", "display_name": "Demo Operator"}
_APPROVER = {"type": "user", "id": "approver1", "display_name": "Demo Approver"}


def _make_approved_skill(client, monkeypatch):
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda cfg: FakeOdooClient())
    monkeypatch.setattr(
        "erpguard.product.services.build_readonly_client", lambda cfg: FakeOdooClient()
    )

    conn = client.post(
        "/v1/odoo/connections",
        json={
            "name": "Odoo Demo",
            "url": "https://empresa.odoo.com",
            "database": "empresa-prod",
            "username": "usuario@empresa.com",
            "api_key": "super-secret",
            "formula_model": "x_sale_formula_line",
            "capacity_field": "x_studio_capacidad_ml",
            "field_mappings": {
                "product_capacity_ml": "x_studio_capacidad_ml",
                "formula_sale_line_id": "x_studio_sale_line_id",
                "formula_fragrance_id": "x_studio_fragancia_id",
                "formula_ml_per_unit": "x_studio_ml_por_unidad",
                "formula_ml_total": "x_studio_ml_total_pedido",
            },
        },
    )
    assert conn.status_code == 200
    connection_id = conn.json()["connection_id"]

    analysis = client.post(
        f"/v1/product/connections/{connection_id}/analyze",
        json={
            "include_samples": True,
            "sample_limits": {"sales_orders": 5, "products": 5, "custom_fields": 50},
            "max_opportunities": 5,
        },
    )
    assert analysis.status_code == 200
    opportunity_id = analysis.json()["opportunities"][0]["opportunity_id"]

    draft = client.post(f"/v1/product/opportunities/{opportunity_id}/draft")
    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]

    compiled = client.post(f"/v1/product/automation-drafts/{draft_id}/compile-skill")
    assert compiled.status_code == 200
    skill_id = compiled.json()["skill_id"]

    proof = client.post(f"/v1/product/skills/{skill_id}/dry-run-proof")
    assert proof.status_code == 200

    req = client.post(
        f"/v1/product/skills/{skill_id}/approval-request",
        json={
            "requested_by": _OPERATOR,
            "reason": "Ready for governance approval.",
            "context": {},
        },
    )
    assert req.status_code == 200

    decision = client.post(
        f"/v1/product/skills/{skill_id}/approval-decision",
        json={
            "decided_by": _APPROVER,
            "decision": "approve",
            "reason": "Guards verified.",
        },
    )
    assert decision.status_code == 200

    gate = client.post(f"/v1/product/skills/{skill_id}/activation-gate")
    assert gate.status_code == 200

    return skill_id


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


def test_run_write_readiness_assessment(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assert response.status_code == 200
    body = response.json()
    assert body["assessment_id"].startswith("write_assessment_")
    assert body["skill_id"] == skill_id
    assert body["status"] == "completed"
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert "overall_risk_level" in body
    assert isinstance(body["write_candidates"], list)
    assert isinstance(body["risk_matrix"], list)


def test_assessment_unknown_skill():
    client = TestClient(app)
    response = client.post("/v1/product/skills/ghost_skill/write-readiness-assessment")
    assert response.status_code == 404


def test_get_write_readiness_assessment(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")

    response = client.get(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == skill_id
    assert body["can_execute_real_writes"] is False


def test_all_write_candidates_blocked(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    body = response.json()
    for candidate in body["write_candidates"]:
        assert candidate["blocked"] is True
        assert candidate["blocked_reason"] == "ALLOW_REAL_ODOO_WRITES=false"


def test_all_risk_entries_blocked_for_real_writes(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    body = response.json()
    for entry in body["risk_matrix"]:
        assert entry["can_execute_real_writes"] is False


# ---------------------------------------------------------------------------
# Impact preview
# ---------------------------------------------------------------------------


def test_generate_impact_preview(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]

    response = client.post(
        f"/v1/product/write-readiness-assessments/{assessment_id}/impact-preview"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["impact_id"].startswith("write_impact_")
    assert body["assessment_id"] == assessment_id
    assert body["can_execute_real_writes"] is False
    assert "affected_models" in body
    assert "estimated_record_count" in body


def test_impact_preview_unknown_assessment():
    client = TestClient(app)
    response = client.post(
        "/v1/product/write-readiness-assessments/ghost_assessment/impact-preview"
    )
    assert response.status_code == 404


def test_get_write_impact_preview(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/impact-preview")

    response = client.get(f"/v1/product/skills/{skill_id}/write-impact-preview")
    assert response.status_code == 200
    assert response.json()["can_execute_real_writes"] is False


# ---------------------------------------------------------------------------
# Rollback plan
# ---------------------------------------------------------------------------


def test_draft_rollback_plan(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]

    response = client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/rollback-plan")
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"].startswith("write_rollback_")
    assert body["assessment_id"] == assessment_id
    assert body["can_execute_real_writes"] is False
    assert isinstance(body["rollback_steps"], list)
    assert len(body["rollback_steps"]) >= 1
    assert body["estimated_rollback_time_minutes"] >= 1


def test_rollback_plan_unknown_assessment():
    client = TestClient(app)
    response = client.post("/v1/product/write-readiness-assessments/ghost_assessment/rollback-plan")
    assert response.status_code == 404


def test_get_rollback_plan(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/rollback-plan")

    response = client.get(f"/v1/product/skills/{skill_id}/write-rollback-plan")
    assert response.status_code == 200
    assert response.json()["can_execute_real_writes"] is False


# ---------------------------------------------------------------------------
# Certification
# ---------------------------------------------------------------------------


def _full_write_readiness_flow(client, skill_id):
    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/impact-preview")
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/rollback-plan")
    return assessment_id


def test_certify_write_readiness(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    _full_write_readiness_flow(client, skill_id)

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    assert response.status_code == 200
    body = response.json()
    assert body["certification_id"].startswith("write_cert_")
    assert body["skill_id"] == skill_id
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert body["approved_for_real_execution"] is False
    assert body["can_certify_real_execution"] is False
    assert body["dual_approval_required"] is True
    assert "certification_status" in body
    assert "overall_risk_level" in body


def test_certification_blocked_without_assessment():
    client = TestClient(app)
    response = client.post("/v1/product/skills/ghost_skill/write-readiness-certification")
    assert response.status_code == 404


def test_certification_blocked_without_impact_preview(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    assert response.status_code == 404


def test_certification_blocked_without_rollback_plan(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assessment_id = assessment.json()["assessment_id"]
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/impact-preview")

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    assert response.status_code == 404


def test_certification_evidence_has_security_flags(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    _full_write_readiness_flow(client, skill_id)

    response = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    body = response.json()
    evidence = body["evidence"]
    assert evidence["can_execute_real_writes"] is False
    assert evidence["approved_for_real_execution"] is False
    assert evidence["ALLOW_REAL_ODOO_WRITES"] is False


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_write_readiness_summary_empty(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.get(f"/v1/product/skills/{skill_id}/write-readiness-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["has_assessment"] is False
    assert body["has_certification"] is False
    assert body["can_execute_real_writes"] is False
    assert body["approved_for_real_execution"] is False


def test_write_readiness_summary_full_flow(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    _full_write_readiness_flow(client, skill_id)
    client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")

    response = client.get(f"/v1/product/skills/{skill_id}/write-readiness-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["has_assessment"] is True
    assert body["has_impact_preview"] is True
    assert body["has_rollback_plan"] is True
    assert body["has_certification"] is True
    assert body["can_execute_real_writes"] is False
    assert body["approved_for_real_execution"] is False
    assert body["overall_risk_level"] is not None
    assert body["certification_status"] is not None


# ---------------------------------------------------------------------------
# Security invariants — hardcoded across all responses
# ---------------------------------------------------------------------------


def test_certification_never_enables_real_writes(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)
    _full_write_readiness_flow(client, skill_id)

    cert = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    body = cert.json()
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert body["approved_for_real_execution"] is False
    assert body["can_certify_real_execution"] is False
