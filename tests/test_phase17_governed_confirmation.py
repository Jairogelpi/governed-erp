"""Phase 17 -- governed Odoo sales-order confirmation.

The transport is an in-memory staging double. No test contacts Odoo, while
the same bounded connector path is used by the live XML-RPC transport.
"""

from __future__ import annotations

import copy
import json
import xmlrpc.client
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.execution.permit_service import _safe_execution_error


class _ConfirmationTransport:
    def __init__(self, *, amount_total: float = 250.0, unexpected_invoice: bool = False) -> None:
        self.confirm_calls = 0
        self.fingerprint_revision = "v1"
        self.unexpected_invoice = unexpected_invoice
        self.snapshot = {
            "order_id": 42,
            "name": "S00042",
            "state": "draft",
            "partner_id": 7,
            "company_id": 1,
            "currency_id": 1,
            "amount_total": amount_total,
            "client_reference": "TFM-PHASE17",
            "write_date": "2026-07-30 10:00:00",
            "lines": [
                {
                    "id": 101,
                    "product_id": 9,
                    "product_name": "Safe product",
                    "quantity": 2.0,
                    "price_unit": 125.0,
                    "price_subtotal": 250.0,
                    "write_date": "2026-07-30 10:00:00",
                }
            ],
            "pickings": [],
            "invoices": [],
            "payments": [],
            "purchase_orders": [],
            "manufacturing_orders": [],
            "effect_observation_issues": [],
        }

    def read_confirmation_snapshot(self, order_id: int) -> dict:
        assert order_id == 42
        return copy.deepcopy(self.snapshot)

    def read_confirmation_automation_fingerprint(self, order_id: int) -> dict:
        assert order_id == 42
        return {
            "server_version": "19.0-test",
            "installed_modules": ["account", "sale", "sale_stock", "stock"],
            "automated_action_count": 0,
            "custom_sale_order_fields": [],
            "model_access": {
                model: {"read": True, "write": model == "sale.order"}
                for model in (
                    "sale.order",
                    "stock.picking",
                    "account.move",
                    "account.payment",
                    "purchase.order",
                    "mrp.production",
                )
            },
            "configuration_signals": {
                "effect_models_observable": True,
                "revision": self.fingerprint_revision,
            },
            "blocking_issues": [],
        }

    def confirm_order(self, order_id: int) -> None:
        assert order_id == 42
        self.confirm_calls += 1
        self.snapshot["state"] = "sale"
        self.snapshot["write_date"] = "2026-07-30 10:01:00"
        self.snapshot["pickings"] = [
            {
                "id": 501,
                "name": "WH/OUT/00501",
                "state": "confirmed",
                "write_date": "2026-07-30 10:01:00",
            }
        ]
        if self.unexpected_invoice:
            self.snapshot["invoices"] = [
                {
                    "id": 601,
                    "name": "INV/00601",
                    "state": "posted",
                    "move_type": "out_invoice",
                    "write_date": "2026-07-30 10:01:00",
                }
            ]


def _identity(tenant_id: str, role: str) -> tuple[str, dict[str, str]]:
    user_id = f"phase17-{role}-{uuid4().hex}"
    db = SessionLocal()
    try:
        db.add(
            IdentityUser(
                id=user_id,
                email=f"{user_id}@example.test",
                display_name=f"Phase 17 {role}",
            )
        )
        db.add(
            IdentityMembership(
                id=f"membership-{uuid4().hex}",
                tenant_id=tenant_id,
                user_id=user_id,
                role_name=role,
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()
    return user_id, {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'phase17-auth')}"}


def _seed_runtime(tenant_id: str, *, environment: str = "staging") -> tuple[str, str]:
    suffix = uuid4().hex
    secret_id = f"secret-{suffix}"
    connection_id = f"connection-{suffix}"
    skill_id = f"skill-{suffix}"
    package = {
        "capability_manifest": [
            {
                "capability": "sales.order.confirm",
                "connector_id": "odoo",
                "version": "1",
                "safety_tier": "R3_governed_staging_only",
                "supports_execution": True,
            }
        ]
    }
    db = SessionLocal()
    try:
        db.add(
            EncryptedSecret(
                id=secret_id,
                tenant_id=tenant_id,
                ciphertext="not-used-by-injected-test-transport",
                fingerprint="phase17-test",
                status="active",
            )
        )
        db.add(
            UnifiedConnection(
                id=connection_id,
                tenant_id=tenant_id,
                name=f"Phase 17 staging {suffix}",
                connector_type="odoo",
                endpoint="https://odoo-staging.example.test",
                auth_type="api_key",
                secret_ref=secret_id,
                metadata_json=json.dumps(
                    {
                        "environment": environment,
                        "confirmation_amount_ceiling": 500.0,
                    }
                ),
                status="active",
                created_by="phase17-test",
            )
        )
        db.add(
            SkillPackage(
                id=skill_id,
                tenant_id=tenant_id,
                candidate_id=f"candidate-{suffix}",
                proof_id=f"proof-{suffix}",
                process_key="quote_to_order",
                candidate_version="17.0.0",
                connector_id="odoo",
                status="approved",
                package_json=json.dumps(package),
                validation_result_json="{}",
                package_hash=f"hash-{suffix}",
            )
        )
        db.commit()
    finally:
        db.close()
    return connection_id, skill_id


def _setup(
    monkeypatch,
    *,
    environment: str = "staging",
    amount_total: float = 250.0,
    unexpected_invoice: bool = False,
):
    monkeypatch.setattr(settings, "auth_secret", "phase17-auth")
    monkeypatch.setattr(settings, "allow_odoo_governed_confirmation", True)
    init_db()
    transport = _ConfirmationTransport(
        amount_total=amount_total,
        unexpected_invoice=unexpected_invoice,
    )
    monkeypatch.setattr(
        ConnectorApplicationService,
        "_odoo_write_transport_factory",
        lambda self, connection: (lambda context: transport),
    )
    tenant_id = f"phase17-tenant-{uuid4().hex}"
    planner_id, planner_headers = _identity(tenant_id, "operator")
    approver_id, approver_headers = _identity(tenant_id, "admin")
    connection_id, skill_id = _seed_runtime(tenant_id, environment=environment)
    return (
        TestClient(app),
        transport,
        planner_id,
        planner_headers,
        approver_id,
        approver_headers,
        connection_id,
        skill_id,
    )


def _plan(client: TestClient, headers: dict, connection_id: str, skill_id: str):
    return client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "skill_package_id": skill_id,
            "capability": "sales.order.confirm",
            "idempotency_key": f"phase17-{uuid4().hex}",
            "capability_payload": {"order_id": 42},
        },
    )


def _approve(client: TestClient, run: dict, headers: dict):
    approval = client.post(
        "/v1/approvals",
        headers=headers,
        json={"scope": run["required_approval_scope"]},
    )
    assert approval.status_code == 201, approval.text
    return client.post(
        f"/v1/runs/{run['id']}/approve",
        headers=headers,
        json={"approval_ids": [approval.json()["id"]], "ttl_seconds": 300},
    )


def test_safe_staging_confirmation_succeeds_with_complete_evidence(monkeypatch):
    client, transport, _, planner, _, approver, connection_id, skill_id = _setup(monkeypatch)
    plan_response = _plan(client, planner, connection_id, skill_id)
    assert plan_response.status_code == 201, plan_response.text
    run = plan_response.json()
    assert run["risk"] == "R3"
    assert run["state_snapshot"]["state"] == "draft"
    assert run["control_contract"]["automation_fingerprint"]["complete"] is True
    assert run["control_contract"]["side_effect_budget"]["maximum_created_records"]["account.move"] == 0
    assert run["control_contract_hash"]
    assert run["required_approval_scope"].startswith(f"run:{run['id']}:sales.order.confirm:")
    assert run["cleanup_plan"]["automatic_rollback"] is False

    approval_response = _approve(client, run, approver)
    assert approval_response.status_code == 200, approval_response.text

    execute_response = client.post(f"/v1/runs/{run['id']}/execute", headers=planner)
    assert execute_response.status_code == 200, execute_response.text
    executed = execute_response.json()
    assert executed["status"] == "succeeded"
    assert transport.confirm_calls == 1
    assert executed["verification_result"]["postcondition"]["verified"] is True
    assert executed["verification_result"]["postcondition"]["evidence"]["generated_picking_ids"] == [501]

    evidence_response = client.get(f"/v1/runs/{run['id']}/evidence", headers=planner)
    assert evidence_response.status_code == 200, evidence_response.text
    evidence = evidence_response.json()
    assert evidence["status"] == "succeeded"
    assert evidence["risk"] == "R3"
    assert evidence["sealed_digest"]
    assert len(evidence["approvals"]) == 1
    assert evidence["cleanup_plan"]["mode"] == "manual_governed_compensation"


def test_unexpected_posted_invoice_exceeds_budget_and_materializes_compensation(monkeypatch):
    client, transport, _, planner, _, approver, connection_id, skill_id = _setup(
        monkeypatch,
        unexpected_invoice=True,
    )
    run = _plan(client, planner, connection_id, skill_id).json()
    assert _approve(client, run, approver).status_code == 200

    response = client.post(f"/v1/runs/{run['id']}/execute", headers=planner)

    assert response.status_code == 200, response.text
    executed = response.json()
    assert executed["status"] == "failed"
    assert transport.confirm_calls == 1
    postcondition = executed["verification_result"]["postcondition"]
    assert postcondition["verified"] is False
    evaluation = postcondition["evidence"]["side_effect_evaluation"]
    assert evaluation["status"] == "budget_exceeded"
    assert "forbidden_effect_observed:invoice_creation" in evaluation["violations"]
    assert "forbidden_effect_observed:invoice_posting" in evaluation["violations"]
    assert executed["cleanup_plan"]["affected_records"]["account.move"] == [601]
    assert executed["cleanup_plan"]["automatic_rollback"] is False

    evidence = client.get(f"/v1/runs/{run['id']}/evidence", headers=planner).json()
    assert evidence["status"] == "failed"
    assert evidence["control_contract"]["side_effect_budget"]["forbidden_effects"]
    assert evidence["verification"]["postcondition"]["verified"] is False
    assert evidence["cleanup_plan"]["affected_records"]["account.move"] == [601]


def test_changed_automation_fingerprint_after_approval_is_blocked(monkeypatch):
    client, transport, _, planner, _, approver, connection_id, skill_id = _setup(monkeypatch)
    run = _plan(client, planner, connection_id, skill_id).json()
    assert _approve(client, run, approver).status_code == 200
    transport.fingerprint_revision = "v2"

    blocked = client.post(f"/v1/runs/{run['id']}/execute", headers=planner)

    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "control_contract_changed_since_approval"
    assert transport.confirm_calls == 0


def test_incomplete_automation_fingerprint_blocks_planning(monkeypatch):
    client, transport, _, planner, _, _, connection_id, skill_id = _setup(monkeypatch)
    original = transport.read_confirmation_automation_fingerprint

    def incomplete(order_id: int) -> dict:
        evidence = original(order_id)
        evidence["blocking_issues"] = ["automated_actions_unobservable"]
        return evidence

    transport.read_confirmation_automation_fingerprint = incomplete  # type: ignore[method-assign]
    blocked = _plan(client, planner, connection_id, skill_id)

    assert blocked.status_code == 400
    assert "automated_actions_unobservable" in blocked.json()["detail"]
    assert transport.confirm_calls == 0


def test_confirmation_requires_nonempty_independent_scoped_approval(monkeypatch):
    client, _, planner_id, planner, _, approver, connection_id, skill_id = _setup(monkeypatch)
    run = _plan(client, planner, connection_id, skill_id).json()

    empty = client.post(
        f"/v1/runs/{run['id']}/approve",
        headers=approver,
        json={"approval_ids": []},
    )
    assert empty.status_code == 400
    assert empty.json()["detail"] == "confirmation_requires_independent_approval"

    wrong_scope_approval = client.post(
        "/v1/approvals",
        headers=approver,
        json={"scope": "run:execute"},
    ).json()
    wrong_scope = client.post(
        f"/v1/runs/{run['id']}/approve",
        headers=approver,
        json={"approval_ids": [wrong_scope_approval["id"]]},
    )
    assert wrong_scope.status_code == 400
    assert wrong_scope.json()["detail"] == "confirmation_approval_scope_mismatch"

    approved = _approve(client, run, approver)
    assert approved.status_code == 200
    wrong_executor = client.post(f"/v1/runs/{run['id']}/execute", headers=approver)
    assert wrong_executor.status_code == 400
    assert wrong_executor.json()["detail"] == "confirmation_must_be_executed_by_planning_actor"

    # An admin planning and approving their own run is not independent.
    admin_run = _plan(client, approver, connection_id, skill_id).json()
    self_approval = client.post(
        "/v1/approvals",
        headers=approver,
        json={"scope": admin_run["required_approval_scope"]},
    ).json()
    rejected = client.post(
        f"/v1/runs/{admin_run['id']}/approve",
        headers=approver,
        json={"approval_ids": [self_approval["id"]]},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "confirmation_approval_must_be_independent"
    assert planner_id != self_approval["actor_id"]


def test_changed_state_after_approval_is_blocked_and_evidenced(monkeypatch):
    client, transport, _, planner, _, approver, connection_id, skill_id = _setup(monkeypatch)
    run = _plan(client, planner, connection_id, skill_id).json()
    assert _approve(client, run, approver).status_code == 200

    transport.snapshot["amount_total"] = 251.0
    transport.snapshot["write_date"] = "2026-07-30 10:00:30"
    blocked = client.post(f"/v1/runs/{run['id']}/execute", headers=planner)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "state_changed_since_approval"
    assert transport.confirm_calls == 0

    stored = client.get(f"/v1/runs/{run['id']}", headers=planner)
    assert stored.status_code == 200
    assert stored.json()["status"] == "blocked"
    evidence = client.get(f"/v1/runs/{run['id']}/evidence", headers=planner)
    assert evidence.status_code == 200
    assert evidence.json()["verification"]["current_state_snapshot"]["amount_total"] == 251.0


def test_confirmation_preflight_blocks_non_staging_and_ceiling(monkeypatch):
    client, transport, _, planner, _, _, connection_id, skill_id = _setup(
        monkeypatch,
        environment="production",
    )
    production = _plan(client, planner, connection_id, skill_id)
    assert production.status_code == 400
    assert "confirmation_requires_staging_connection" in production.json()["detail"]
    assert transport.confirm_calls == 0

    client, transport, _, planner, _, _, connection_id, skill_id = _setup(
        monkeypatch,
        amount_total=501.0,
    )
    over_ceiling = _plan(client, planner, connection_id, skill_id)
    assert over_ceiling.status_code == 400
    assert "confirmation_amount_exceeds_ceiling" in over_ceiling.json()["detail"]
    assert transport.confirm_calls == 0


def test_confirmation_is_fail_closed_when_feature_flag_is_disabled(monkeypatch):
    client, transport, _, planner, _, _, connection_id, skill_id = _setup(monkeypatch)
    monkeypatch.setattr(settings, "allow_odoo_governed_confirmation", False)
    blocked = _plan(client, planner, connection_id, skill_id)
    assert blocked.status_code == 400
    assert "governed_confirmation_disabled" in blocked.json()["detail"]
    assert transport.confirm_calls == 0


def test_xmlrpc_fault_preserves_only_bounded_business_diagnostic():
    fault = xmlrpc.client.Fault(
        1,
        "Traceback (most recent call last):\n"
        '  File "/private/server/path.py", line 99, in action_confirm\n'
        "odoo.exceptions.UserError: Confirmation blocked by staging policy",
    )

    diagnostic = _safe_execution_error(fault)

    assert diagnostic == "Fault:odoo.exceptions.UserError: Confirmation blocked by staging policy"
    assert "/private/server/path.py" not in diagnostic
