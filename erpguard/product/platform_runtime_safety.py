from __future__ import annotations

from erpguard.db.repositories import count_write_pilot_runs_recent, list_tenants
from erpguard.product.models import RuntimeSafetyModel
from erpguard.product.platform_kill_switch import (
    _PLATFORM_GLOBAL_KILL_SWITCH,
    _RUNTIME_EXECUTION_KILL_SWITCH,
    _WRITE_PILOT_KILL_SWITCH,
)

_TENANT_CONTROLS_ENABLED = True
_ENVIRONMENT_GUARD_ENABLED = True
_AUDIT_EXPORT_ENABLED = True
_RATE_LIMITS_ENABLED = True
_SECRET_REDACTION_ENFORCED = True

_ALLOW_R1_REAL_WRITE_PILOT = False
_ALLOW_GENERIC_REAL_ODOO_WRITES = False
_ALLOW_R3_R4_REAL_WRITES = False


def _compute_safety_level(
    global_ks: bool,
    runtime_ks: bool,
    write_ks: bool,
    allow_generic: bool,
    allow_r3_r4: bool,
) -> str:
    if allow_generic or allow_r3_r4:
        return "critical"
    if global_ks or runtime_ks or write_ks:
        return "locked"
    return "safe"


class RuntimeSafetyService:
    def __init__(self, session) -> None:
        self.session = session

    def summary(self) -> RuntimeSafetyModel:
        active_tenants = len([t for t in list_tenants(self.session) if t.status == "active"])
        recent_runs = count_write_pilot_runs_recent(self.session, hours=24)

        safety_level = _compute_safety_level(
            _PLATFORM_GLOBAL_KILL_SWITCH,
            _RUNTIME_EXECUTION_KILL_SWITCH,
            _WRITE_PILOT_KILL_SWITCH,
            _ALLOW_GENERIC_REAL_ODOO_WRITES,
            _ALLOW_R3_R4_REAL_WRITES,
        )

        return RuntimeSafetyModel(
            platform_global_kill_switch=_PLATFORM_GLOBAL_KILL_SWITCH,
            runtime_execution_kill_switch=_RUNTIME_EXECUTION_KILL_SWITCH,
            write_pilot_kill_switch=_WRITE_PILOT_KILL_SWITCH,
            tenant_controls_enabled=_TENANT_CONTROLS_ENABLED,
            environment_guard_enabled=_ENVIRONMENT_GUARD_ENABLED,
            audit_export_enabled=_AUDIT_EXPORT_ENABLED,
            rate_limits_enabled=_RATE_LIMITS_ENABLED,
            secret_redaction_enforced=_SECRET_REDACTION_ENFORCED,
            allow_r1_real_write_pilot=_ALLOW_R1_REAL_WRITE_PILOT,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            active_tenant_count=active_tenants,
            recent_write_pilot_runs=recent_runs,
            safety_level=safety_level,
        )
