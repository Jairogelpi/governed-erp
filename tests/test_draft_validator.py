import json

from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import create_connection, create_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.draft_validator import DraftValidatorService
from erpguard.product.models import BusinessAnalysisRequest
from erpguard.product.services import BusinessAnalysisService


class FakeReadOnlyOdooClient:
    def version(self):
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        return 2

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}]
        if model == "ir.model":
            return []
        if model == "sale.order":
            return [{"id": 1, "name": "S00001", "state": "sale", "order_line": []}]
        if model == "product.product":
            return [{"id": 1, "display_name": "Prod", "default_code": "P1"}]
        return []

    def fields_get(self, model, attributes=None):
        return {}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 1
        if model == "product.product":
            return 1
        return 0


_ODOO_CONFIG = {
    "url": "https://example.odoo.com",
    "database": "demo",
    "username": "user@example.com",
    "api_key": "secret",
    "formula_model": "x_sale_formula_line",
    "capacity_field": "x_studio_capacidad_ml",
    "field_mappings": {},
}


def _make_valid_draft(session):
    package = {
        "draft_kind": "non_executable_automation",
        "runtime_mode": "dry_run_only",
        "write_actions": False,
        "guards": ["read_only", "no_odoo_writes", "dry_run_only"],
        "steps": [{"id": "review", "type": "review", "description": "Inspect read-only snapshot."}],
    }
    return create_automation_draft(
        session,
        opportunity_id="opportunity_test",
        scan_id="scan_test",
        snapshot_id="snapshot_test",
        connection_id="conn_test",
        name="Test Draft",
        description="Draft for testing",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json=json.dumps(package),
        status="created",
    )


def test_validator_passes_valid_draft():
    init_db()
    session = SessionLocal()
    draft = _make_valid_draft(session)

    result = DraftValidatorService(session).validate(draft.id)

    assert result.passed is True
    assert result.issues == []
    session.close()


def test_validator_fails_when_write_actions_true():
    init_db()
    session = SessionLocal()
    package = {
        "runtime_mode": "dry_run_only",
        "write_actions": False,
        "guards": ["no_odoo_writes"],
        "steps": [],
    }
    draft = create_automation_draft(
        session,
        opportunity_id="opp_t",
        scan_id="scan_t",
        snapshot_id="snap_t",
        connection_id="conn_t",
        name="Bad Draft",
        description="Bad",
        runtime_mode="dry_run_only",
        write_actions=True,
        draft_json=json.dumps(package),
        status="created",
    )

    result = DraftValidatorService(session).validate(draft.id)

    assert result.passed is False
    codes = [i.code for i in result.issues]
    assert "write_actions_enabled" in codes
    session.close()


def test_validator_fails_when_runtime_mode_wrong():
    init_db()
    session = SessionLocal()
    package = {
        "runtime_mode": "live",
        "write_actions": False,
        "guards": ["no_odoo_writes"],
        "steps": [],
    }
    draft = create_automation_draft(
        session,
        opportunity_id="opp_t2",
        scan_id="scan_t2",
        snapshot_id="snap_t2",
        connection_id="conn_t2",
        name="Bad Mode Draft",
        description="Bad mode",
        runtime_mode="live",
        write_actions=False,
        draft_json=json.dumps(package),
        status="created",
    )

    result = DraftValidatorService(session).validate(draft.id)

    assert result.passed is False
    codes = [i.code for i in result.issues]
    assert "invalid_runtime_mode" in codes
    session.close()


def test_validator_fails_when_no_odoo_writes_guard_missing():
    init_db()
    session = SessionLocal()
    package = {
        "runtime_mode": "dry_run_only",
        "write_actions": False,
        "guards": ["read_only"],
        "steps": [],
    }
    draft = create_automation_draft(
        session,
        opportunity_id="opp_t3",
        scan_id="scan_t3",
        snapshot_id="snap_t3",
        connection_id="conn_t3",
        name="Missing Guard Draft",
        description="Missing guard",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json=json.dumps(package),
        status="created",
    )

    result = DraftValidatorService(session).validate(draft.id)

    assert result.passed is False
    codes = [i.code for i in result.issues]
    assert "missing_no_odoo_writes_guard" in codes
    session.close()


def test_validator_returns_not_found_for_missing_draft():
    init_db()
    session = SessionLocal()

    result = DraftValidatorService(session).validate("automation_draft_does_not_exist")

    assert result.passed is False
    assert result.issues[0].code == "draft_not_found"
    session.close()
