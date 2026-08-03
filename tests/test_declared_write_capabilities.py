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
        self.create_calls = 0
        self._next_id = 1000

    def seed(self, model: str, record_id: int, field: str, value: object) -> None:
        self.rows[(model, record_id)] = {field: value}

    def write_field(self, *, model: str, record_id: int, field: str, value: object) -> None:
        self.write_calls += 1
        self.rows.setdefault((model, record_id), {})[field] = value

    def read_field(self, *, model: str, record_id: int, field: str) -> object:
        return self.rows[(model, record_id)][field]

    def create_record(
        self, *, model: str, values: dict[str, object], idempotency_field: str, idempotency_key: str
    ) -> tuple[int, bool]:
        for (existing_model, record_id), row in self.rows.items():
            if existing_model == model and row.get(idempotency_field) == idempotency_key:
                return record_id, False
        self.create_calls += 1
        record_id = self._next_id
        self._next_id += 1
        self.rows[(model, record_id)] = dict(values)
        return record_id, True


def _plugin(transport: _FakeWriteTransport) -> OdooConnectorPlugin:
    return OdooConnectorPlugin(write_transport_factory=lambda context: transport)


def _lookup(db_session):
    def lookup(cap_id: str) -> DeclaredWriteCapability | None:
        return (
            db_session.query(DeclaredWriteCapability)
            .filter_by(tenant_id="tenant-1", id=cap_id, status="active")
            .one_or_none()
        )

    return lookup


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
    lookup = _lookup(db_session)
    context = _staging_context({"declared_capability_lookup": lookup})

    plan = asyncio.run(plugin.plan_capability(context, f"declared.{draft_row.id}"))
    assert plan.status == "blocked"


def test_runtime_value_outside_declared_range_blocked(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active(db_session, minimum="0", maximum="50")
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 7, "loyalty_discount_pct", 10.0)
    plugin = _plugin(transport)
    lookup = _lookup(db_session)
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
    lookup = _lookup(db_session)
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
    lookup = _lookup(db_session)
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
    lookup = _lookup(db_session)
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


def _declared_and_active_operation(db_session, **declare_kwargs) -> DeclaredWriteCapability:
    service = DeclaredCapabilityService(db_session)
    row = service.declare(tenant_id="tenant-1", created_by="user-1", **declare_kwargs)
    approval = Approval(
        id=f"approval_{uuid4().hex}", tenant_id="tenant-1", scope=DeclaredCapabilityService.approval_scope(row),
        actor_id="user-2",
    )
    db_session.add(approval)
    db_session.commit()
    row = service.approve(tenant_id="tenant-1", capability_id=row.id, approval_id=approval.id, approver_actor_id="user-2")
    return service.activate(tenant_id="tenant-1", capability_id=row.id)


def test_bulk_update_field_capped_at_max_records_per_run(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active_operation(
        db_session, name="bulk_discount", target_model="res.partner", target_field="loyalty_discount_pct",
        field_type="decimal", minimum_value="0", maximum_value="50", max_records_per_run=2,
    )
    transport = _FakeWriteTransport()
    for record_id in (1, 2, 3):
        transport.seed("res.partner", record_id, "loyalty_discount_pct", 0.0)
    plugin = _plugin(transport)
    context = _staging_context({"declared_capability_lookup": _lookup(db_session)})
    capability_name = f"declared.{active_row.id}"

    within_cap = NativeExecutionPlan(
        capability=capability_name, arguments={"record_ids": [1, 2], "value": 15}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, within_cap, permit))
    assert result.status == "ok"
    assert transport.write_calls == 2
    verification = asyncio.run(plugin.verify_execution(context, capability_name, result))
    assert verification.verified is True

    over_cap = NativeExecutionPlan(
        capability=capability_name, arguments={"record_ids": [1, 2, 3], "value": 15}, supports_execution=True,
    )
    over_result = asyncio.run(plugin.execute_capability(context, over_cap, permit))
    assert over_result.status == "blocked"
    assert transport.write_calls == 2


def test_archive_record_is_reversible_field_write(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active_operation(
        db_session, name="archive_stale_partner", target_model="res.partner", operation="archive_record",
    )
    transport = _FakeWriteTransport()
    transport.seed("res.partner", 9, "active", True)
    plugin = _plugin(transport)
    context = _staging_context({"declared_capability_lookup": _lookup(db_session)})
    capability_name = f"declared.{active_row.id}"

    archive_plan = NativeExecutionPlan(
        capability=capability_name, arguments={"record_id": 9, "value": False}, supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, archive_plan, permit))
    assert result.status == "ok"
    assert transport.read_field(model="res.partner", record_id=9, field="active") is False

    restore_plan = NativeExecutionPlan(
        capability=capability_name, arguments={"record_id": 9, "value": True}, supports_execution=True,
    )
    restore_result = asyncio.run(plugin.execute_capability(context, restore_plan, permit))
    assert restore_result.status == "ok"
    assert transport.read_field(model="res.partner", record_id=9, field="active") is True


def test_archive_record_denylisted_model_field_rejected(db_session):
    service = DeclaredCapabilityService(db_session)
    with pytest.raises(DeclaredCapabilityDenied):
        service.declare(
            tenant_id="tenant-1", name="bad_archive", target_model="res.users", operation="archive_record",
            created_by="user-1",
        )


def test_create_record_idempotent_round_trip(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active_operation(
        db_session, name="create_lead", target_model="crm.lead", operation="create_record",
        required_fields={"name": "string", "email_from": "string"}, idempotency_field="name",
    )
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    context = _staging_context({"declared_capability_lookup": _lookup(db_session)})
    capability_name = f"declared.{active_row.id}"
    values = {"name": "erpguard-lead-123", "email_from": "lead@example.com"}

    plan = NativeExecutionPlan(
        capability=capability_name,
        arguments={"values": values, "idempotency_key": "erpguard-lead-123"},
        supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, plan, permit))
    assert result.status == "ok"
    assert result.payload["created"] is True
    assert transport.create_calls == 1

    verification = asyncio.run(plugin.verify_execution(context, capability_name, result))
    assert verification.verified is True

    retry_result = asyncio.run(plugin.execute_capability(context, plan, permit))
    assert retry_result.status == "ok"
    assert retry_result.payload["created"] is False
    assert transport.create_calls == 1
    assert retry_result.payload["record_id"] == result.payload["record_id"]


def test_create_record_rejects_extra_or_missing_fields(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_declared_write_capabilities", True)
    active_row = _declared_and_active_operation(
        db_session, name="create_lead", target_model="crm.lead", operation="create_record",
        required_fields={"name": "string", "email_from": "string"}, idempotency_field="name",
    )
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    context = _staging_context({"declared_capability_lookup": _lookup(db_session)})
    capability_name = f"declared.{active_row.id}"

    missing_field_plan = NativeExecutionPlan(
        capability=capability_name,
        arguments={"values": {"name": "x"}, "idempotency_key": "x"},
        supports_execution=True,
    )
    permit = ExecutionPermit(permit_id="permit-1", capability=capability_name, approved=True)
    result = asyncio.run(plugin.execute_capability(context, missing_field_plan, permit))
    assert result.status == "blocked"

    extra_field_plan = NativeExecutionPlan(
        capability=capability_name,
        arguments={"values": {"name": "x", "email_from": "x@example.com", "phone": "123"}, "idempotency_key": "x"},
        supports_execution=True,
    )
    extra_result = asyncio.run(plugin.execute_capability(context, extra_field_plan, permit))
    assert extra_result.status == "blocked"
    assert transport.create_calls == 0


def test_create_record_denylisted_required_field_rejected(db_session):
    service = DeclaredCapabilityService(db_session)
    with pytest.raises(DeclaredCapabilityDenied):
        service.declare(
            tenant_id="tenant-1", name="bad_create", target_model="res.users", operation="create_record",
            required_fields={"login": "string"}, idempotency_field="login", created_by="user-1",
        )
