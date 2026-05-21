import json

from fastapi.testclient import TestClient

from apps.api.main import app


class FakeReadOnlyOdooClient:
    def version(self):
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        return 2

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model" and domain == [["model", "in", ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]]:
            return [{"model": m} for m in ["res.users", "sale.order", "product.product"]]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]:
            return []
        if model == "sale.order":
            return [{"id": 42, "name": "S00042", "state": "sale", "order_line": [90]}]
        if model == "sale.order.line":
            return [{"id": 90, "product_id": [15, "Perfume 100ML"], "product_uom_qty": 10, "price_unit": 12.3}]
        if model == "product.product":
            return [{"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100"}]
        return []

    def fields_get(self, model, attributes=None):
        if model == "sale.order":
            return {"id": {}, "name": {}, "state": {}, "order_line": {}, "amount_total": {}}
        if model == "sale.order.line":
            return {"id": {}, "order_id": {}, "product_id": {}, "product_uom_qty": {}, "price_unit": {}, "price_subtotal": {}}
        if model == "product.product":
            return {"id": {}, "display_name": {}, "default_code": {}, "tracking": {}, "standard_price": {}}
        if model == "product.template":
            return {"id": {}, "display_name": {}, "default_code": {}}
        return {}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 2
        if model == "product.product":
            return 1
        return 0


def _make_connection_and_draft(client, monkeypatch):
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: FakeReadOnlyOdooClient())
    monkeypatch.setattr("erpguard.product.services.build_readonly_client", lambda config: FakeReadOnlyOdooClient())

    conn_response = client.post(
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
    assert conn_response.status_code == 200
    connection_id = conn_response.json()["connection_id"]

    analysis_response = client.post(
        f"/v1/product/connections/{connection_id}/analyze",
        json={"include_samples": True, "sample_limits": {"sales_orders": 5, "products": 5, "custom_fields": 50}, "max_opportunities": 5},
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    opportunity_id = analysis["opportunities"][0]["opportunity_id"]

    draft_response = client.post(f"/v1/product/opportunities/{opportunity_id}/draft")
    assert draft_response.status_code == 200
    return draft_response.json()["draft_id"]


def test_sprint3_full_review_validate_compile_proof_flow(monkeypatch):
    client = TestClient(app)
    draft_id = _make_connection_and_draft(client, monkeypatch)

    review_response = client.get(f"/v1/product/automation-drafts/{draft_id}/review")
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["review_id"].startswith("draft_review_")
    assert review["status"] == "ready_to_compile"
    guard_names = [g["name"] for g in review["guards"]]
    assert "no_odoo_writes" in guard_names
    assert "dry_run_only" in guard_names
    assert "requires_approval_before_activation" in guard_names

    validate_response = client.post(f"/v1/product/automation-drafts/{draft_id}/validate")
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation["passed"] is True
    assert validation["issues"] == []

    compile_response = client.post(f"/v1/product/automation-drafts/{draft_id}/compile-skill")
    assert compile_response.status_code == 200
    compiled = compile_response.json()
    assert compiled["skill_id"].startswith("skill_")
    assert compiled["write_actions"] is False
    assert compiled["runtime_mode"] == "dry_run_only"
    assert compiled["requires_approval_before_activation"] is True
    assert "no_odoo_writes" in compiled["guards"]

    compiled_skill_response = client.get(f"/v1/product/automation-drafts/{draft_id}/compiled-skill")
    assert compiled_skill_response.status_code == 200
    compiled_lookup = compiled_skill_response.json()
    assert compiled_lookup["skill_id"] == compiled["skill_id"]

    proof_response = client.post(f"/v1/product/skills/{compiled['skill_id']}/dry-run-proof")
    assert proof_response.status_code == 200
    proof = proof_response.json()
    assert proof["proof_id"].startswith("dry_run_proof_")
    assert proof["write_actions"] is False
    assert proof["runtime_mode"] == "dry_run_only"
    assert proof["requires_approval_before_activation"] is True
    assert proof["cases_total"] > 0
    assert proof["cases_passed"] == proof["cases_total"]
    assert proof["status"] == "passed"


def test_sprint3_review_idempotent(monkeypatch):
    client = TestClient(app)
    draft_id = _make_connection_and_draft(client, monkeypatch)

    review1 = client.get(f"/v1/product/automation-drafts/{draft_id}/review").json()
    review2 = client.get(f"/v1/product/automation-drafts/{draft_id}/review").json()
    assert review1["review_id"] == review2["review_id"]


def test_sprint3_not_found_for_missing_draft(monkeypatch):
    client = TestClient(app)
    response = client.get("/v1/product/automation-drafts/automation_draft_does_not_exist/review")
    assert response.status_code == 404


def test_sprint3_compile_returns_422_on_invalid_draft():
    client = TestClient(app)
    import json as _json
    from erpguard.db.repositories import create_automation_draft
    from erpguard.db.session import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    package = {
        "runtime_mode": "live",
        "write_actions": True,
        "guards": [],
        "steps": [],
    }
    draft = create_automation_draft(
        session,
        opportunity_id="opp_bad",
        scan_id="scan_bad",
        snapshot_id="snap_bad",
        connection_id="conn_bad",
        name="Bad Draft",
        description="invalid",
        runtime_mode="live",
        write_actions=True,
        draft_json=_json.dumps(package),
        status="created",
    )
    session.close()

    compile_response = client.post(f"/v1/product/automation-drafts/{draft.id}/compile-skill")
    assert compile_response.status_code == 422
    body = compile_response.json()
    assert body["error"]["code"] == "draft_validation_failed"
