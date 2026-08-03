"""User-declared write capabilities: declare -> approve -> activate -> plan
-> execute -> verify, against an injected fake write transport (same
technique test_phase16_odoo_quote_draft.py already uses -- never a live
Odoo call in the automated suite).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from erpguard.config import settings
from erpguard.db.session import SessionLocal, init_db
from erpguard.connectors.odoo.plugin import OdooConnectorPlugin
from erpguard.connectors.sdk.models import ConnectorContext, ExecutionPermit, NativeExecutionPlan
from erpguard.db.model_packages.declared_capabilities import DeclaredWriteCapability
from erpguard.db.model_packages.execution import Approval
from erpguard.domain.declared_capabilities.denylist import is_denylisted
from erpguard.domain.declared_capabilities.service import (
    DeclaredCapabilityDenied,
    DeclaredCapabilityService,
    DeclaredCapabilityTransitionError,
)


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


class _FakeWriteTransport:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], dict[str, object]] = {}
        self.write_calls = 0

    def seed(self, model: str, record_id: int, field: str, value: object) -> None:
        self.rows[(model, record_id)] = {field: value}

    def write_field(self, *, model: str, record_id: int, field: str, value: object) -> None:
        self.write_calls += 1
        self.rows.setdefault((model, record_id), {})[field] = value

    def read_field(self, *, model: str, record_id: int, field: str) -> object:
        return self.rows[(model, record_id)][field]


def _plugin(transport: _FakeWriteTransport) -> OdooConnectorPlugin:
    return OdooConnectorPlugin(write_transport_factory=lambda context: transport)


def _staging_context(services: dict | None = None) -> ConnectorContext:
    merged = {"connection_metadata": {"environment": "staging"}}
    merged.update(services or {})
    return ConnectorContext(tenant_id="tenant-1", connection_id="conn-1", services=merged)


@pytest.mark.parametrize(
    "model,field",
    [("res.users", "login"), ("ir.model", "name"), ("account.move", "state"), ("sale.order", "amount_total")],
)
def test_denylist_rejects_at_declare_time(db_session, model, field):
    service = DeclaredCapabilityService(db_session)
    with pytest.raises(DeclaredCapabilityDenied):
        service.declare(
            tenant_id="tenant-1", name="bad", target_model=model, target_field=field,
            field_type="string", created_by="user-1",
        )


def test_creator_cannot_approve_own_declaration(db_session):
    service = DeclaredCapabilityService(db_session)
    row = service.declare(
        tenant_id="tenant-1", name="loyalty_tier", target_model="res.partner", target_field="loyalty_tier",
        field_type="string", created_by="user-1",
    )
    approval = Approval(
        id=f"approval_{uuid4().hex}", tenant_id="tenant-1", scope=DeclaredCapabilityService.approval_scope(row),
        actor_id="user-1",
    )
    db_session.add(approval)
    db_session.commit()
    with pytest.raises(Exception):
        service.approve(tenant_id="tenant-1", capability_id=row.id, approval_id=approval.id, approver_actor_id="user-1")


def _declared_and_active(db_session, *, minimum=None, maximum=None, field_type="decimal") -> DeclaredWriteCapability:
    service = DeclaredCapabilityService(db_session)
    row = service.declare(
        tenant_id="tenant-1", name="discount_pct", target_model="res.partner", target_field="loyalty_discount_pct",
        field_type=field_type, created_by="user-1", minimum_value=minimum, maximum_value=maximum,
    )
    approval = Approval(
        id=f"approval_{uuid4().hex}", tenant_id="tenant-1", scope=DeclaredCapabilityService.approval_scope(row),
        actor_id="user-2",
    )
    db_session.add(approval)
    db_session.commit()
    row = service.approve(tenant_id="tenant-1", capability_id=row.id, approval_id=approval.id, approver_actor_id="user-2")
    return service.activate(tenant_id="tenant-1", capability_id=row.id)


def test_only_active_capability_usable_by_plan(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    service = DeclaredCapabilityService(db_session)
    draft_row = service.declare(
        tenant_id="tenant-1", name="x", target_model="res.partner", target_field="x", field_type="string",
        created_by="user-1",
    )
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    lookup = lambda cap_id: db_session.query(DeclaredWriteCapability).filter_by(
        tenant_id="tenant-1", id=cap_id, status="active"
    ).one_or_none()
    context = _staging_context({"declared_capability_lookup": lookup})

    plan = asyncio.run(plugin.plan_capability(context, f"declared.{draft_row.id}"))
    assert plan.status == "blocked"


def test_runtime_value_outside_declared_range_blocked(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active(db_session, minimum="0", maximum="50")
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 7, "loyalty_discount_pct", 10.0)
    plugin = _plugin(transport)
    lookup = lambda cap_id: db_session.query(DeclaredWriteCapability).filter_by(
        tenant_id="tenant-1", id=cap_id, status="active"
    ).one_or_none()
    context = _staging_context({"declared_capability_lookup": lookup})

    plan = NativeExecutionPlan(
        capability=f"declared.{active_row.id}", arguments={"record_id": 7, "value": 999}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=plan.capability, approved=True)
    result = asyncio.run(plugin.execute_capability(context, plan, permit))

    assert result.status == "blocked"
    assert transport.write_calls == 0


def test_feature_flag_defaults_off_blocks_active_capability(db_session):
    assert settings.allow_declared_write_capabilities is False
    active_row = _declared_and_active(db_session, minimum="0", maximum="50")
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 7, "loyalty_discount_pct", 10.0)
    plugin = _plugin(transport)
    lookup = lambda cap_id: db_session.query(DeclaredWriteCapability).filter_by(
        tenant_id="tenant-1", id=cap_id, status="active"
    ).one_or_none()
    context = _staging_context({"declared_capability_lookup": lookup})

    plan = NativeExecutionPlan(
        capability=f"declared.{active_row.id}", arguments={"record_id": 7, "value": 20}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=plan.capability, approved=True)
    result = asyncio.run(plugin.execute_capability(context, plan, permit))

    assert result.status == "blocked"
    assert transport.write_calls == 0


def test_full_round_trip_declare_approve_activate_plan_execute_verify(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active(db_session, minimum="0", maximum="50")
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 7, "loyalty_discount_pct", 10.0)
    plugin = _plugin(transport)
    lookup = lambda cap_id: db_session.query(DeclaredWriteCapability).filter_by(
        tenant_id="tenant-1", id=cap_id, status="active"
    ).one_or_none()
    context = _staging_context({"declared_capability_lookup": lookup})
    capability_name = f"declared.{active_row.id}"

    plan = asyncio.run(plugin.plan_capability(context, capability_name))
    assert plan.status == "planned"

    full_plan = NativeExecutionPlan(
        capability=capability_name, arguments={"record_id": 7, "value": 25}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, full_plan, permit))
    assert result.status == "ok"
    assert transport.write_calls == 1

    verification = asyncio.run(plugin.verify_execution(context, capability_name, result))
    assert verification.verified is True
    assert transport.read_field(model="res.partner", record_id=7, field="loyalty_discount_pct") == 25


def test_postcondition_failure_marks_verification_failed(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active(db_session, minimum="0", maximum="50")
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 7, "loyalty_discount_pct", 10.0)
    plugin = _plugin(transport)
    lookup = lambda cap_id: db_session.query(DeclaredWriteCapability).filter_by(
        tenant_id="tenant-1", id=cap_id, status="active"
    ).one_or_none()
    context = _staging_context({"declared_capability_lookup": lookup})
    capability_name = f"declared.{active_row.id}"

    full_plan = NativeExecutionPlan(
        capability=capability_name, arguments={"record_id": 7, "value": 25}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, full_plan, permit))

    # simulate drift after write (another process changes the field)
    transport.rows[("res.partner", 7)]["loyalty_discount_pct"] = 999

    verification = asyncio.run(plugin.verify_execution(context, capability_name, result))
    assert verification.verified is False
    assert verification.status == "verification_failed"


def test_denylist_helper_covers_prefixes():
    assert is_denylisted(model="res.users", field="login")
    assert is_denylisted(model="ir.model.fields", field="name")
    assert is_denylisted(model="account.move", field="state")
    assert not is_denylisted(model="res.partner", field="loyalty_discount_pct")


def test_invalid_transition_rejected(db_session):
    service = DeclaredCapabilityService(db_session)
    row = service.declare(
        tenant_id="tenant-1", name="x", target_model="res.partner", target_field="x", field_type="string",
        created_by="user-1",
    )
    with pytest.raises(DeclaredCapabilityTransitionError):
        service.activate(tenant_id="tenant-1", capability_id=row.id)
