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
            return [{"id": 42, "name": "S00042", "state": "sale", "order_line": [90]}]
        if model == "sale.order.line":
            return [
                {
                    "id": 90,
                    "product_id": [15, "Perfume 100ML"],
                    "product_uom_qty": 10,
                    "price_unit": 12.3,
                }
            ]
        if model == "product.product":
            return [{"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100"}]
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


def _make_compiled_skill(client, monkeypatch):
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

    return skill_id


def test_sprint4_full_approval_gate_governance_flow(monkeypatch):
    client = TestClient(app)
    skill_id = _make_compiled_skill(client, monkeypatch)

    req_response = client.post(
        f"/v1/product/skills/{skill_id}/approval-request",
        json={
            "requested_by": _OPERATOR,
            "reason": "Ready for governance approval.",
            "context": {},
        },
    )
    assert req_response.status_code == 200
    req = req_response.json()
    assert req["request_id"].startswith("approval_request_")
    assert req["status"] == "pending"
    assert req["can_execute_real_writes"] is False

    get_req_response = client.get(f"/v1/product/skills/{skill_id}/approval-request")
    assert get_req_response.status_code == 200
    assert get_req_response.json()["request_id"] == req["request_id"]

    decision_response = client.post(
        f"/v1/product/skills/{skill_id}/approval-decision",
        json={
            "decided_by": _APPROVER,
            "decision": "approve",
            "reason": "Guards verified. Dry-run proof passed.",
        },
    )
    assert decision_response.status_code == 200
    decision = decision_response.json()
    assert decision["decision"] == "approve"
    assert decision["can_execute_real_writes"] is False
    assert decision["approved_for_real_execution"] is False

    history_response = client.get(f"/v1/product/skills/{skill_id}/approval-history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1
    assert all(d["can_execute_real_writes"] is False for d in history)
    assert all(d["approved_for_real_execution"] is False for d in history)

    gate_response = client.post(f"/v1/product/skills/{skill_id}/activation-gate")
    assert gate_response.status_code == 200
    gate = gate_response.json()
    assert gate["gate_id"].startswith("gate_eval_")
    assert gate["gate_status"] == "open"
    assert gate["can_activate"] is True
    assert gate["can_execute_real_writes"] is False
    assert gate["approved_for_real_execution"] is False

    summary_response = client.get(f"/v1/product/skills/{skill_id}/governance-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["skill_id"] == skill_id
    assert summary["governance_state"] == "approved_dry_run_only"
    assert summary["can_execute_real_writes"] is False
    assert summary["approved_for_real_execution"] is False
    assert (
        "dry-run" in summary["next_required_action"].lower()
        or "gate" in summary["next_required_action"].lower()
        or "approved" in summary["next_required_action"].lower()
    )


def test_sprint4_reject_decision(monkeypatch):
    client = TestClient(app)
    skill_id = _make_compiled_skill(client, monkeypatch)

    client.post(
        f"/v1/product/skills/{skill_id}/approval-request",
        json={
            "requested_by": _OPERATOR,
            "reason": "Review this.",
            "context": {},
        },
    )
    decision_response = client.post(
        f"/v1/product/skills/{skill_id}/approval-decision",
        json={
            "decided_by": _APPROVER,
            "decision": "reject",
            "reason": "Does not meet criteria.",
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["decision"] == "reject"
    assert decision_response.json()["can_execute_real_writes"] is False

    summary = client.get(f"/v1/product/skills/{skill_id}/governance-summary").json()
    assert summary["governance_state"] == "rejected"


def test_sprint4_invalid_decision_returns_422(monkeypatch):
    client = TestClient(app)
    skill_id = _make_compiled_skill(client, monkeypatch)
    client.post(
        f"/v1/product/skills/{skill_id}/approval-request",
        json={
            "requested_by": _OPERATOR,
            "reason": "Review.",
            "context": {},
        },
    )

    response = client.post(
        f"/v1/product/skills/{skill_id}/approval-decision",
        json={
            "decided_by": _APPROVER,
            "decision": "execute_now",
            "reason": "bad decision",
        },
    )
    assert response.status_code == 422


def test_sprint4_not_found_for_missing_skill(monkeypatch):
    client = TestClient(app)
    response = client.get("/v1/product/skills/skill_does_not_exist/governance-summary")
    assert response.status_code == 404
