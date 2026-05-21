from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.platform_secret_redactor import SecretRedactionService
from erpguard.product.platform_tenant import TenantService
from erpguard.product.platform_kill_switch import KillSwitchService
from erpguard.product.platform_runtime_safety import RuntimeSafetyService
from erpguard.product.platform_policy import PlatformPolicyService
from erpguard.product.models import PolicyEvaluationRequestModel


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


# ── SecretRedactionService ─────────────────────────────────────────────────

class TestSecretRedactionService:
    def test_redacts_known_keys(self):
        svc = SecretRedactionService()
        result = svc.redact({"api_key": "abc123", "name": "visible"})
        assert result["api_key"] == "***REDACTED***"
        assert result["name"] == "visible"

    def test_redacts_password_key(self):
        svc = SecretRedactionService()
        result = svc.redact({"password": "secret", "user": "admin"})
        assert result["password"] == "***REDACTED***"

    def test_redacts_nested_secrets(self):
        svc = SecretRedactionService()
        # "credentials" itself is a sensitive key — entire value is redacted
        result = svc.redact({"credentials": {"token": "tok123", "host": "localhost"}})
        assert result["credentials"] == "***REDACTED***"
        # use a non-sensitive wrapper to test deep recursion
        result2 = svc.redact({"config": {"token": "tok123", "host": "localhost"}})
        assert result2["config"]["token"] == "***REDACTED***"
        assert result2["config"]["host"] == "localhost"

    def test_redacts_list_items(self):
        svc = SecretRedactionService()
        result = svc.redact([{"api_key": "k1"}, {"name": "safe"}])
        assert result[0]["api_key"] == "***REDACTED***"
        assert result[1]["name"] == "safe"

    def test_leaves_non_sensitive_keys_intact(self):
        svc = SecretRedactionService()
        result = svc.redact({"name": "ok", "value": 42, "flag": True})
        assert result == {"name": "ok", "value": 42, "flag": True}

    def test_redacts_extra_keys(self):
        svc = SecretRedactionService()
        result = svc.redact_keys({"my_secret_field": "hidden", "public": "ok"}, extra_keys={"my_secret_field"})
        assert result["my_secret_field"] == "***REDACTED***"
        assert result["public"] == "ok"

    def test_handles_none(self):
        svc = SecretRedactionService()
        assert svc.redact(None) is None

    def test_handles_primitive(self):
        svc = SecretRedactionService()
        assert svc.redact("plain string") == "plain string"
        assert svc.redact(42) == 42


# ── TenantService ──────────────────────────────────────────────────────────

class TestTenantService:
    def test_create_tenant(self, db_session):
        svc = TenantService(db_session)
        tenant = svc.create(name="Acme Corp", environment="staging")
        assert tenant.tenant_id.startswith("tenant_")
        assert tenant.name == "Acme Corp"
        assert tenant.environment == "staging"
        assert tenant.status == "active"
        assert tenant.secret_redaction_enforced is True

    def test_create_tenant_default_roles(self, db_session):
        svc = TenantService(db_session)
        tenant = svc.create(name="Roles Test", environment="staging")
        role_names = {r.name for r in tenant.roles}
        assert "operator" in role_names
        assert "approver" in role_names
        assert "admin" in role_names

    def test_get_tenant(self, db_session):
        svc = TenantService(db_session)
        created = svc.create(name="GetMe", environment="production")
        fetched = svc.get(created.tenant_id)
        assert fetched.tenant_id == created.tenant_id
        assert fetched.name == "GetMe"

    def test_get_tenant_not_found(self, db_session):
        from erpguard.core.errors import ObjectNotFoundError
        svc = TenantService(db_session)
        with pytest.raises(ObjectNotFoundError):
            svc.get("tenant_nonexistent_xyz")

    def test_default_kill_switches_all_false(self, db_session):
        svc = TenantService(db_session)
        tenant = svc.create(name="KS Test", environment="staging")
        ks = tenant.kill_switches
        assert ks.global_kill_switch is False
        assert ks.runtime_execution_kill_switch is False
        assert ks.write_pilot_kill_switch is False


# ── KillSwitchService ──────────────────────────────────────────────────────

class TestKillSwitchService:
    def test_activate_kill_switch(self, db_session):
        tenant = TenantService(db_session).create(name="KS Activate", environment="staging")
        ks_svc = KillSwitchService(db_session)
        event = ks_svc.activate(
            tenant.tenant_id,
            "write_pilot_kill_switch",
            activated_by={"type": "user", "id": "u1"},
            reason="Test activation",
        )
        assert event.switch_name == "write_pilot_kill_switch"
        assert event.action == "activate"
        assert event.tenant_id == tenant.tenant_id

    def test_deactivate_kill_switch(self, db_session):
        tenant = TenantService(db_session).create(name="KS Deactivate", environment="staging")
        ks_svc = KillSwitchService(db_session)
        ks_svc.activate(tenant.tenant_id, "write_pilot_kill_switch", {"type": "user", "id": "u1"}, "on")
        event = ks_svc.deactivate(tenant.tenant_id, "write_pilot_kill_switch", {"type": "user", "id": "u1"}, "off")
        assert event.action == "deactivate"

    def test_invalid_switch_name_raises(self, db_session):
        tenant = TenantService(db_session).create(name="KS Invalid", environment="staging")
        ks_svc = KillSwitchService(db_session)
        with pytest.raises(ValueError, match="Unknown kill switch"):
            ks_svc.activate(tenant.tenant_id, "unknown_switch", {}, "test")

    def test_active_switches_for_tenant(self, db_session):
        tenant = TenantService(db_session).create(name="KS Active List", environment="staging")
        ks_svc = KillSwitchService(db_session)
        assert ks_svc.active_switches_for_tenant(tenant.tenant_id) == []
        ks_svc.activate(tenant.tenant_id, "write_pilot_kill_switch", {}, "test")
        active = ks_svc.active_switches_for_tenant(tenant.tenant_id)
        assert "tenant_write_pilot_kill_switch" in active

    def test_list_events(self, db_session):
        tenant = TenantService(db_session).create(name="KS Events", environment="staging")
        ks_svc = KillSwitchService(db_session)
        ks_svc.activate(tenant.tenant_id, "global_kill_switch", {}, "reason1")
        ks_svc.deactivate(tenant.tenant_id, "global_kill_switch", {}, "reason2")
        events = ks_svc.list_events(tenant.tenant_id)
        assert len(events) >= 2


# ── RuntimeSafetyService ───────────────────────────────────────────────────

class TestRuntimeSafetyService:
    def test_summary_default_safe(self, db_session):
        svc = RuntimeSafetyService(db_session)
        summary = svc.summary()
        assert summary.safety_level == "safe"
        assert summary.allow_generic_real_odoo_writes is False
        assert summary.allow_r3_r4_real_writes is False
        assert summary.platform_global_kill_switch is False

    def test_summary_locked_when_kill_switch_active(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.platform_runtime_safety._PLATFORM_GLOBAL_KILL_SWITCH", True)
        svc = RuntimeSafetyService(db_session)
        summary = svc.summary()
        assert summary.safety_level == "locked"

    def test_summary_critical_when_generic_writes_enabled(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.platform_runtime_safety._ALLOW_GENERIC_REAL_ODOO_WRITES", True)
        svc = RuntimeSafetyService(db_session)
        summary = svc.summary()
        assert summary.safety_level == "critical"

    def test_r3_r4_always_false_in_summary(self, db_session):
        svc = RuntimeSafetyService(db_session)
        summary = svc.summary()
        assert summary.allow_r3_r4_real_writes is False

    def test_active_tenant_count_includes_created(self, db_session):
        TenantService(db_session).create(name="RT Count", environment="staging")
        svc = RuntimeSafetyService(db_session)
        summary = svc.summary()
        assert summary.active_tenant_count >= 1


# ── PlatformPolicyService ──────────────────────────────────────────────────

class TestPlatformPolicyService:
    def test_operator_can_execute_real_read(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "operator"},
            action="execute_real_read",
            resource="some_resource",
        )
        result = svc.evaluate(req)
        assert result.allowed is True

    def test_operator_cannot_approve_write_pilot(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "operator"},
            action="approve_write_pilot",
            resource="some_resource",
        )
        result = svc.evaluate(req)
        assert result.allowed is False

    def test_approver_can_activate_kill_switch(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "approver"},
            action="activate_kill_switch",
            resource="platform",
        )
        result = svc.evaluate(req)
        assert result.allowed is True

    def test_admin_can_manage_tenant(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "admin"},
            action="manage_tenant",
            resource="tenant_123",
        )
        result = svc.evaluate(req)
        assert result.allowed is True

    def test_unknown_role_blocked(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "ghost"},
            action="execute_real_read",
            resource="x",
        )
        result = svc.evaluate(req)
        assert result.allowed is False

    def test_unknown_action_blocked(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "admin"},
            action="do_something_evil",
            resource="x",
        )
        result = svc.evaluate(req)
        assert result.allowed is False

    def test_kill_switch_blocks_allowed_action(self, db_session):
        tenant = TenantService(db_session).create(name="Policy KS", environment="staging")
        KillSwitchService(db_session).activate(tenant.tenant_id, "global_kill_switch", {}, "test")
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(
            actor={"role": "admin"},
            action="execute_real_read",
            resource="x",
        )
        result = svc.evaluate(req, tenant_id=tenant.tenant_id)
        assert result.allowed is False
        assert len(result.kill_switches_active) > 0

    def test_result_always_has_writes_false(self, db_session):
        svc = PlatformPolicyService(db_session)
        req = PolicyEvaluationRequestModel(actor={"role": "admin"}, action="execute_real_read", resource="x")
        result = svc.evaluate(req)
        assert result.allow_generic_real_odoo_writes is False
        assert result.allow_r3_r4_real_writes is False
