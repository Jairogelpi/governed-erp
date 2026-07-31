"""Spec 92 Sec 8 -- pricing scenario draft, via the dedicated
`sales.quote.create_pricing_scenario_draft` connector capability (distinct
from the plain `quote.create_draft` used by the unrelated Phase 16 feature --
Sec 8.1 requires this because the pricing-scenario write carries
recommendation/margin evidence and its own live preconditions).

Full recommendation -> approval -> action draft -> `PermitService.plan()`
end to end via the public API; execution itself is exercised by
monkeypatching `ConnectorApplicationService._odoo_write_transport_factory`
to a deterministic fake (same technique `test_phase16_odoo_quote_draft.py`
uses at the connector layer, just injected one level up so the full
governed pipeline runs without a live Odoo).
"""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.shadow.service import ShadowService

from test_phase14_skill_compiler import _build_submitted_candidate_with_proof, _identity
from test_phase16_6_opportunity_roi_engine import _seed_margin_analysis, _segment
from test_phase19_skill_deployment_lifecycle import _shadow_deployment_row


class _FakeWriteTransport:
    def __init__(self) -> None:
        self.orders: dict[str, int] = {}
        self.rows: dict[int, dict] = {}
        self.lines: dict[int, list[dict]] = {}
        self._next_id = 500
        self.create_calls = 0

    def find_by_client_reference(self, client_reference: str) -> int | None:
        return self.orders.get(client_reference)

    def create_draft(
        self, *, partner_id: int, lines: list[dict], client_reference: str,
        company_id: int | None = None, pricelist_id: int | None = None,
    ) -> int:
        self.create_calls += 1
        order_id = self._next_id
        self._next_id += 1
        self.orders[client_reference] = order_id
        self.rows[order_id] = {
            "id": order_id, "state": "draft", "partner_id": partner_id, "client_order_ref": client_reference,
            "company_id": company_id, "pricelist_id": pricelist_id,
        }
        self.lines[order_id] = list(lines)
        return order_id

    def read_order(self, order_id: int) -> dict:
        return self.rows[order_id]

    def read_partner(self, partner_id: int) -> dict:
        return {"id": partner_id, "active": True}

    def read_products(self, product_ids: list[int]) -> list[dict]:
        return [{"id": pid, "active": True, "sale_ok": True, "name": f"Product {pid}"} for pid in product_ids]

    def read_pricing_scenario_snapshot(self, order_id: int) -> dict:
        order = self.rows[order_id]
        return {
            "order_id": order_id,
            "state": order["state"],
            "partner_id": order["partner_id"],
            "company_id": order.get("company_id"),
            "currency_id": order.get("currency_id", 1),
            "pricelist_id": order.get("pricelist_id"),
            "client_reference": order["client_order_ref"],
            "lines": [
                {
                    "product_id": int(line["product_id"]),
                    "quantity": float(line["quantity"]),
                    "price_unit": float(line["price_unit"]),
                }
                for line in self.lines.get(order_id, [])
            ],
            "invoice_count": 0,
            "picking_count": 0,
            "purchase_order_count": 0,
            "manufacturing_order_count": 0,
        }


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "allow_pricing_scenario_draft", True)
    init_db()
    tenant_id = f"pricing-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _active_odoo_skill_package(client: TestClient, headers: dict, monkeypatch, tenant_id: str) -> str:
    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={
            "connector_id": "odoo",
            "workflow_steps": [
                {"step_name": "create_draft", "capability": "sales.quote.create_pricing_scenario_draft"}
            ],
        },
    )
    assert compile_resp.status_code == 201, compile_resp.text
    skill_id = compile_resp.json()["id"]
    assert client.post(f"/v1/skills/{skill_id}/versions/{version}/approve", headers=headers).status_code == 200

    monkeypatch.setattr(
        ShadowService, "dashboard", lambda self, *, tenant_id, deployment_id: {"recommendation": "eligible_for_canary"}
    )
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{skill_id}/promote-canary", headers=headers,
        json={"shadow_deployment_id": deployment_id, "reason": "test"},
    ).status_code == 200
    assert client.post(
        f"/v1/skills/{skill_id}/promote-active", headers=headers, json={"reason": "go"}
    ).status_code == 200
    return process_key


def _odoo_connection(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/v1/connections",
        headers=headers,
        json={
            "name": f"odoo-conn-{uuid4().hex[:8]}",
            "connector_type": "odoo",
            "endpoint": "https://odoo.example.test",
            "auth_type": "api_key",
            "secret": "fake-odoo-secret",
            "metadata": {"database": "test_db", "username": "test_user", "environment": "staging"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _seed_opportunity(tenant_id: str) -> str:
    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    analysis_id = _seed_margin_analysis(
        tenant_id, status="ready", product_drivers=product_drivers, customer_drivers={"current": [], "comparison": []}
    )
    from erpguard.application.opportunity.service import OpportunityEngineService

    db = SessionLocal()
    try:
        rows = OpportunityEngineService(db).generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        return rows[0].id
    finally:
        db.close()


def _approved_recommendation(client: TestClient, headers: dict, tenant_id: str, opportunity_id: str) -> dict:
    create_resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "customer_discount_review",
            "title": "Discount scenario",
            "selected_action_template": "customer_discount_quote_scenario_v1",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    recommendation = create_resp.json()
    assert client.post(f"/v1/recommendations/{recommendation['id']}/submit", headers=headers).status_code == 200

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": recommendation["approval_scope"]}
    ).json()["id"]
    approve_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/approve",
        headers=approver_headers,
        json={"approval_id": approval_id},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return approve_resp.json()


_VALID_PRICING_INPUTS = {
    "partner_id": 42,
    "company_id": 1,
    "currency_id": 1,
    "pricelist_id": 1,
    "lines": [
        {
            "product_id": 7,
            "quantity": 2,
            "proposed_unit_price": "80.00",
            "cost_reference": "60.00",
            "minimum_margin_percent": "10.0",
        }
    ],
}


def test_feature_flag_defaults_off(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"pricing-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)
    opportunity_id = _seed_opportunity(tenant_id)
    recommendation = _approved_recommendation(client, headers, tenant_id, opportunity_id)

    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts",
        headers=headers,
        json={"process_key": "irrelevant", "pricing_inputs": _VALID_PRICING_INPUTS},
    )
    assert draft_resp.status_code == 400, draft_resp.text
    assert "pricing_scenario_draft_disabled" in draft_resp.json()["detail"]


def test_margin_floor_violation_blocks(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    opportunity_id = _seed_opportunity(tenant_id)
    recommendation = _approved_recommendation(client, headers, tenant_id, opportunity_id)

    bad_inputs = {
        **_VALID_PRICING_INPUTS,
        "lines": [{**_VALID_PRICING_INPUTS["lines"][0], "proposed_unit_price": "61.00", "minimum_margin_percent": "50.0"}],
    }
    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts",
        headers=headers,
        json={"process_key": "irrelevant", "pricing_inputs": bad_inputs},
    )
    assert draft_resp.status_code == 400, draft_resp.text
    assert "margin_floor_violated" in draft_resp.json()["detail"]


def test_no_generic_write_method_exists():
    """Structural, not behavioral -- OdooConnectorPlugin exposes no
    model/method/execute_raw entry point at all."""

    from erpguard.connectors.odoo.plugin import OdooConnectorPlugin

    plugin = OdooConnectorPlugin()
    for forbidden in ("execute_raw", "call_method", "model", "method"):
        assert not hasattr(plugin, forbidden)


def test_draft_created_retry_idempotent_and_no_credential_in_evidence(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key = _active_odoo_skill_package(client, headers, monkeypatch, tenant_id)
    connection_id = _odoo_connection(client, headers)
    opportunity_id = _seed_opportunity(tenant_id)
    recommendation = _approved_recommendation(client, headers, tenant_id, opportunity_id)

    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts",
        headers=headers,
        json={"process_key": process_key, "connection_id": connection_id, "pricing_inputs": _VALID_PRICING_INPUTS},
    )
    assert draft_resp.status_code == 201, draft_resp.text
    draft = draft_resp.json()
    assert "secret" not in str(draft).lower() and "credential" not in str(draft).lower()

    assert client.post(f"/v1/action-drafts/{draft['id']}/validate", headers=headers).status_code == 200

    transport = _FakeWriteTransport()
    monkeypatch.setattr(
        ConnectorApplicationService, "_odoo_write_transport_factory", lambda self, connection: (lambda context: transport)
    )

    plan_resp = client.post(
        f"/v1/action-drafts/{draft['id']}/plan-run", headers=headers, json={"idempotency_key": f"idem-{uuid4().hex}"}
    )
    assert plan_resp.status_code == 200, plan_resp.text
    run_id = plan_resp.json()["converted_run_id"]
    assert run_id is not None

    # retry conversion is idempotent -- same run
    plan_resp_2 = client.post(
        f"/v1/action-drafts/{draft['id']}/plan-run", headers=headers, json={"idempotency_key": f"idem-{uuid4().hex}"}
    )
    assert plan_resp_2.status_code == 200, plan_resp_2.text
    assert plan_resp_2.json()["converted_run_id"] == run_id

    approval_resp = client.post("/v1/approvals", headers=headers, json={"scope": "run:execute"})
    approval_id = approval_resp.json()["id"]
    approve_run_resp = client.post(
        f"/v1/runs/{run_id}/approve", headers=headers, json={"approval_ids": [approval_id], "ttl_seconds": 900}
    )
    assert approve_run_resp.status_code == 200, approve_run_resp.text

    execute_resp = client.post(f"/v1/runs/{run_id}/execute", headers=headers)
    assert execute_resp.status_code == 200, execute_resp.text
    executed = execute_resp.json()
    assert executed["status"] == "succeeded"
    assert transport.create_calls == 1

    # second execute is a no-op re-verify path, not a second write
    execute_resp_2 = client.post(f"/v1/runs/{run_id}/execute", headers=headers)
    assert transport.create_calls == 1
