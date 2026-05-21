"""Sprint 5 — API integration tests for the execution sandbox."""
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
        if model == "sale.order": return [{"id": 42, "name": "S00042", "state": "sale", "order_line": [90]}]
        if model == "sale.order.line": return [{"id": 90, "product_id": [15, "P 100ML"], "product_uom_qty": 10, "price_unit": 12.3}]
        if model == "product.product": return [{"id": 15, "display_name": "P 100ML", "default_code": "P100"}]
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


_OPERATOR = {"type": "user", "id": "op1", "display_name": "Demo Operator"}
_APPROVER = {"type": "user", "id": "approver1", "display_name": "Demo Approver"}


def _make_approved_skill(client, monkeypatch):
    """Create a fully approved compiled skill ready for sandbox execution."""
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
        "decided_by": _APPROVER, "decision": "approve", "reason": "Guards verified.",
    })
    assert decision.status_code == 200
    assert decision.json()["decision"] == "approve"

    gate = client.post(f"/v1/product/skills/{skill_id}/activation-gate")
    assert gate.status_code == 200
    assert gate.json()["can_activate"] is True

    return skill_id


# ---------------------------------------------------------------------------
# Policy check endpoint
# ---------------------------------------------------------------------------

def test_policy_check_returns_blocked_for_unknown_skill():
    client = TestClient(app)
    response = client.get("/v1/product/skills/nonexistent_skill/execution-policy")
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is False
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert len(body["violations"]) > 0


def test_policy_check_passes_for_approved_skill(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.get(f"/v1/product/skills/{skill_id}/execution-policy")
    assert response.status_code == 200
    body = response.json()
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert body["passed"] is True


# ---------------------------------------------------------------------------
# Execution request lifecycle
# ---------------------------------------------------------------------------

def test_create_execution_request_for_approved_skill(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    response = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    assert response.status_code == 201
    body = response.json()
    assert body["request_id"].startswith("execution_request_")
    assert body["skill_id"] == skill_id
    assert body["status"] == "pending"
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert body["idempotency_key"].startswith("idem_")


def test_execution_request_idempotency(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    inputs = {"dry_run": True, "ref": "SO-IDEM"}
    payload = {"requested_by": _OPERATOR, "inputs": inputs}

    r1 = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json=payload)
    assert r1.status_code == 201
    id1 = r1.json()["request_id"]

    r2 = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json=payload)
    assert r2.status_code == 200
    assert r2.json()["_idempotent_duplicate"] is True
    assert r2.json()["request_id"] == id1


def test_list_execution_requests(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True, "ref": "A"},
    })

    response = client.get(f"/v1/product/skills/{skill_id}/execution-requests")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert all(r["can_execute_real_writes"] is False for r in response.json())


def test_get_execution_request_by_id(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    created = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = created.json()["request_id"]

    response = client.get(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}")
    assert response.status_code == 200
    assert response.json()["request_id"] == request_id


# ---------------------------------------------------------------------------
# Execution run — dry-run sandbox
# ---------------------------------------------------------------------------

def test_run_execution_produces_dry_run_result(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = req.json()["request_id"]

    run_response = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    assert run_response.status_code == 200
    body = run_response.json()
    assert body["run_id"].startswith("execution_run_")
    assert body["status"] == "completed"
    assert body["can_execute_real_writes"] is False
    assert body["real_erp_writes_enabled"] is False
    assert body["plan"]["can_execute_real_writes"] is False
    assert body["plan"]["real_erp_writes_enabled"] is False


def test_run_execution_plan_has_steps(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = req.json()["request_id"]

    run_response = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    body = run_response.json()
    assert body["plan"]["total_steps"] >= 1
    for step in body["plan"]["steps"]:
        assert step["step_id"].startswith("step_")


def test_get_execution_run_by_id(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    run_id = run.json()["run_id"]

    get_response = client.get(f"/v1/product/skills/{skill_id}/execution-runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run_id


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

def test_execution_timeline_returns_steps(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    run_id = run.json()["run_id"]

    timeline_response = client.get(f"/v1/product/skills/{skill_id}/execution-runs/{run_id}/timeline")
    assert timeline_response.status_code == 200
    tl = timeline_response.json()
    assert tl["run_id"] == run_id
    assert tl["can_execute_real_writes"] is False
    assert tl["real_erp_writes_enabled"] is False
    assert tl["total_steps"] >= 1


# ---------------------------------------------------------------------------
# Blocked write evidence
# ---------------------------------------------------------------------------

def test_blocked_writes_list_is_returned(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {"dry_run": True},
    })
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    run_id = run.json()["run_id"]

    blocked_response = client.get(f"/v1/product/skills/{skill_id}/execution-runs/{run_id}/blocked-writes")
    assert blocked_response.status_code == 200
    assert isinstance(blocked_response.json(), list)


# ---------------------------------------------------------------------------
# Security invariants
# ---------------------------------------------------------------------------

def test_execution_request_never_exposes_real_writes_flag(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {},
    })
    body = req.json()
    assert body.get("can_execute_real_writes") is False
    assert body.get("real_erp_writes_enabled") is False


def test_execution_run_never_exposes_real_writes_flag(monkeypatch):
    client = TestClient(app)
    skill_id = _make_approved_skill(client, monkeypatch)

    req = client.post(f"/v1/product/skills/{skill_id}/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {},
    })
    request_id = req.json()["request_id"]
    run = client.post(f"/v1/product/skills/{skill_id}/execution-requests/{request_id}/run")
    body = run.json()
    assert body.get("can_execute_real_writes") is False
    assert body.get("real_erp_writes_enabled") is False
    plan = body.get("plan", {})
    assert plan.get("can_execute_real_writes") is False
    assert plan.get("real_erp_writes_enabled") is False


def test_execution_request_rejected_for_unknown_skill():
    client = TestClient(app)
    response = client.post("/v1/product/skills/ghost_skill/execution-requests", json={
        "requested_by": _OPERATOR, "inputs": {},
    })
    assert response.status_code == 404
