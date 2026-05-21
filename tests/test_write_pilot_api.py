"""Sprint 8 — API integration tests for the first real write pilot."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


class FakeOdooClient:
    def version(self): return {"server_version": "19.0-20260513"}
    def authenticate(self): return 2
    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module": return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model" and domain == [["model", "in", ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]]:
            return [{"model": m} for m in ["res.users", "sale.order", "product.product"]]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]: return []
        if model == "sale.order": return [{"id": 42, "name": "S00042", "state": "sale", "order_line": [90], "amount_total": 500.0}]
        if model == "sale.order.line": return [{"id": 90, "product_id": [15, "P 100ML"], "product_uom_qty": 10, "price_unit": 12.3}]
        if model == "product.product": return [{"id": 15, "display_name": "P 100ML", "default_code": "P100", "tracking": "none", "standard_price": 9.0}]
        return []
    def fields_get(self, model, attributes=None):
        if model == "sale.order": return {"id": {}, "name": {}, "state": {}, "order_line": {}, "amount_total": {}}
        if model == "sale.order.line": return {"id": {}, "order_id": {}, "product_id": {}, "product_uom_qty": {}, "price_unit": {}, "price_subtotal": {}}
        if model == "product.product": return {"id": {}, "display_name": {}, "default_code": {}, "tracking": {}, "standard_price": {}}
        if model == "product.template": return {"id": {}, "display_name": {}, "default_code": {}}
        return {}
    def search_count(self, model, domain):
        if model == "sale.order": return 2
        if model == "product.product": return 1
        return 0


class FakeOdooPilotClient:
    """Fake pilot write client for tests — only implements create for mail.message."""
    def create(self, model: str, vals: dict) -> int:
        assert model == "mail.message", f"Only mail.message allowed, got {model}"
        return 9999

    def version(self): return {"server_version": "19.0"}
    def authenticate(self): return 2
    def search_read(self, model, domain, fields, limit=None): return []
    def fields_get(self, model, attributes=None): return {}
    def search_count(self, model, domain): return 0


_OPERATOR = {"type": "user", "id": "op1", "display_name": "Demo Operator"}
_APPROVER_1 = {"type": "user", "id": "approver1", "display_name": "Demo Approver 1"}
_APPROVER_2 = {"type": "user", "id": "approver2", "display_name": "Demo Approver 2"}

_PILOT_BODY = {
    "requested_by": _OPERATOR,
    "approver_1": _APPROVER_1,
    "approver_2": _APPROVER_2,
    "target_res_model": "sale.order",
    "target_res_id": 42,
    "payload": {"body": "<p>ERPGuard Sprint 8 pilot audit note.</p>"},
}


def _make_approved_skill(client, monkeypatch):
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda cfg: FakeOdooClient())
    monkeypatch.setattr("erpguard.product.services.build_readonly_client", lambda cfg: FakeOdooClient())

    conn = client.post("/v1/odoo/connections", json={
        "name": "Odoo Demo", "url": "https://empresa.odoo.com", "database": "empresa-prod",
        "username": "usuario@empresa.com", "api_key": "super-secret",
        "formula_model": "x_sale_formula_line", "capacity_field": "x_studio_capacidad_ml",
        "field_mappings": {
            "product_capacity_ml": "x_studio_capacidad_ml", "formula_sale_line_id": "x_studio_sale_line_id",
            "formula_fragrance_id": "x_studio_fragancia_id", "formula_ml_per_unit": "x_studio_ml_por_unidad",
            "formula_ml_total": "x_studio_ml_total_pedido",
        },
    })
    assert conn.status_code == 200
    connection_id = conn.json()["connection_id"]

    analysis = client.post(f"/v1/product/connections/{connection_id}/analyze", json={
        "include_samples": True, "sample_limits": {"sales_orders": 5, "products": 5, "custom_fields": 50}, "max_opportunities": 5,
    })
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

    req = client.post(f"/v1/product/skills/{skill_id}/approval-request", json={
        "requested_by": _OPERATOR, "reason": "Ready for governance approval.", "context": {},
    })
    assert req.status_code == 200

    decision = client.post(f"/v1/product/skills/{skill_id}/approval-decision", json={
        "decided_by": _APPROVER_1, "decision": "approve", "reason": "Guards verified.",
    })
    assert decision.status_code == 200

    gate = client.post(f"/v1/product/skills/{skill_id}/activation-gate")
    assert gate.status_code == 200

    return skill_id


def _make_certified_skill(client, monkeypatch):
    skill_id = _make_approved_skill(client, monkeypatch)
    assessment = client.post(f"/v1/product/skills/{skill_id}/write-readiness-assessment")
    assert assessment.status_code == 200
    assessment_id = assessment.json()["assessment_id"]
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/impact-preview")
    client.post(f"/v1/product/write-readiness-assessments/{assessment_id}/rollback-plan")
    cert = client.post(f"/v1/product/skills/{skill_id}/write-readiness-certification")
    assert cert.status_code == 200
    return skill_id


# ---------------------------------------------------------------------------
# Pilot request
# ---------------------------------------------------------------------------

def test_create_write_pilot_request(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["request_id"].startswith("wp_req_")
    assert body["skill_id"] == skill_id
    assert body["target_model"] == "mail.message"
    assert body["status"] == "pending"
    assert body["allow_r1_real_write_pilot"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_create_write_pilot_request_idempotent(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    r1 = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    assert r1.status_code == 201
    r2 = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    assert r2.status_code == 200
    assert r1.json()["request_id"] == r2.json()["request_id"]
    assert r2.json()["_idempotent_duplicate"] is True


def test_pilot_request_rejected_for_unknown_skill():
    client = TestClient(app)
    response = client.post("/v1/product/skills/ghost_skill/write-pilot/request", json=_PILOT_BODY)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Policy check
# ---------------------------------------------------------------------------

def test_policy_check_blocked_by_default(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]

    response = client.post(f"/v1/product/write-pilot/requests/{request_id}/policy-check")
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is False
    assert body["allow_r1_real_write_pilot"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
    assert body["target_model"] == "mail.message"
    assert body["target_whitelisted"] is True
    codes = [v["code"] for v in body["violations"]]
    assert "feature_flag_disabled" in codes


def test_policy_check_unknown_request():
    client = TestClient(app)
    response = client.post("/v1/product/write-pilot/requests/ghost_req/policy-check")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Execution — blocked by default
# ---------------------------------------------------------------------------

def test_execute_blocked_by_feature_flag(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]

    response = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("wp_run_")
    assert body["status"] == "blocked"
    assert body["executed_action"] == "blocked_by_feature_flag"
    assert body["allow_r1_real_write_pilot"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_execute_unknown_request():
    client = TestClient(app)
    response = client.post("/v1/product/write-pilot/requests/ghost_req/execute")
    assert response.status_code == 404


def test_execute_idempotent_returns_same_run(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]

    run1 = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    run2 = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    assert run1.json()["run_id"] == run2.json()["run_id"]


# ---------------------------------------------------------------------------
# Execution — with feature flag enabled (monkeypatched)
# ---------------------------------------------------------------------------

def test_execute_succeeds_when_flag_enabled(monkeypatch):
    client = TestClient(app)
    skill_id = _make_certified_skill(client, monkeypatch)
    monkeypatch.setattr("erpguard.product.write_pilot_executor._ALLOW_R1_REAL_WRITE_PILOT", True)
    monkeypatch.setattr("erpguard.product.write_pilot_policy._ALLOW_R1_REAL_WRITE_PILOT", True)
    monkeypatch.setattr("erpguard.product.write_pilot_executor.build_pilot_write_client", lambda cfg: FakeOdooPilotClient())

    import uuid
    unique_body = dict(_PILOT_BODY)
    unique_body["payload"] = {"body": f"<p>Pilot test {uuid.uuid4().hex}</p>"}

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=unique_body)
    assert req.status_code == 201
    request_id = req.json()["request_id"]

    response = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["executed_action"] == "mail.message.create"
    assert body["allow_r1_real_write_pilot"] is True
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
    assert body["result"]["new_message_id"] == 9999


def test_execute_forbidden_model_raises(monkeypatch):
    from erpguard.adapters.odoo.pilot_write_client import OdooPilotWriteClient, PilotWriteViolationError

    class FakeInner:
        def _execute_kw(self, model, method, args, kwargs):
            return 1

    client_obj = OdooPilotWriteClient(FakeInner())
    with pytest.raises(PilotWriteViolationError):
        client_obj.create("sale.order", {"name": "S/001"})


# ---------------------------------------------------------------------------
# Get run & evidence
# ---------------------------------------------------------------------------

def test_get_write_pilot_run(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    run_id = run.json()["run_id"]

    response = client.get(f"/v1/product/write-pilot/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["run_id"] == run_id


def test_get_write_pilot_run_unknown():
    client = TestClient(app)
    response = client.get("/v1/product/write-pilot/runs/ghost_run")
    assert response.status_code == 404


def test_list_write_pilot_evidence(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    run_id = run.json()["run_id"]

    response = client.get(f"/v1/product/write-pilot/runs/{run_id}/evidence")
    assert response.status_code == 200
    evidence = response.json()
    assert isinstance(evidence, list)
    assert len(evidence) >= 1
    for ev in evidence:
        assert ev["target_model"] == "mail.message"
        assert ev["run_id"] == run_id
        assert ev["allow_generic_real_odoo_writes"] is False


def test_evidence_always_has_idempotency_key(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    run_id = run.json()["run_id"]

    evidence = client.get(f"/v1/product/write-pilot/runs/{run_id}/evidence").json()
    for ev in evidence:
        assert ev["idempotency_key"].startswith("wp_idem_")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def test_write_pilot_history(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)

    response = client.get(f"/v1/product/skills/{skill_id}/write-pilot/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    assert all(r["target_model"] == "mail.message" for r in history)
    assert all(r["allow_r1_real_write_pilot"] is False for r in history)
    assert all(r["allow_generic_real_odoo_writes"] is False for r in history)


# ---------------------------------------------------------------------------
# Security invariants — feature flags always false in all responses
# ---------------------------------------------------------------------------

def test_run_always_has_generic_writes_disabled(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/write-pilot/requests/{request_id}/execute")
    body = run.json()
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_request_always_has_generic_writes_disabled(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/write-pilot/request", json=_PILOT_BODY)
    body = req.json()
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
