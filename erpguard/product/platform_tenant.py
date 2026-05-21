from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_tenant,
    get_tenant,
    list_tenants,
    suspend_tenant,
    update_tenant_kill_switches,
)
from erpguard.product.models import (
    TenantKillSwitchConfig,
    TenantModel,
    TenantRateLimitConfig,
    TenantRoleModel,
)

_DEFAULT_ROLES = [
    {"name": "operator", "permissions": ["execute_real_read", "request_write_pilot"]},
    {"name": "approver", "permissions": ["approve_write_pilot", "activate_kill_switch", "view_audit_export"]},
    {"name": "admin", "permissions": ["execute_real_read", "request_write_pilot", "approve_write_pilot", "activate_kill_switch", "view_audit_export", "manage_tenant"]},
]


class TenantService:
    def __init__(self, session) -> None:
        self.session = session

    def create(self, name: str, environment: str = "staging") -> TenantModel:
        kill_switches = {"global_kill_switch": False, "runtime_execution_kill_switch": False, "write_pilot_kill_switch": False}
        rate_limits = {"max_write_pilots_per_day": 10, "max_live_reads_per_hour": 100}
        secret_scope = {"redaction_enforced": True, "redacted_keys": ["api_key", "password", "secret", "token", "credential", "private_key"]}

        row = create_tenant(
            session=self.session,
            name=name,
            environment=environment,
            kill_switch_json=json.dumps(kill_switches),
            rate_limit_json=json.dumps(rate_limits),
            roles_json=json.dumps(_DEFAULT_ROLES),
            secret_scope_json=json.dumps(secret_scope),
        )
        return self._row_to_model(row)

    def get(self, tenant_id: str) -> TenantModel:
        row = get_tenant(self.session, tenant_id)
        if row is None:
            raise ObjectNotFoundError(f"Tenant '{tenant_id}' not found.")
        return self._row_to_model(row)

    def list_all(self) -> list[TenantModel]:
        return [self._row_to_model(r) for r in list_tenants(self.session)]

    def suspend(self, tenant_id: str) -> TenantModel:
        row = suspend_tenant(self.session, tenant_id)
        if row is None:
            raise ObjectNotFoundError(f"Tenant '{tenant_id}' not found.")
        return self._row_to_model(row)

    @staticmethod
    def _row_to_model(row) -> TenantModel:
        ks = json.loads(row.kill_switch_json)
        rl = json.loads(row.rate_limit_json)
        roles_raw = json.loads(row.roles_json)
        ss = json.loads(row.secret_scope_json)
        return TenantModel(
            tenant_id=row.id,
            name=row.name,
            environment=row.environment,
            status=row.status,
            kill_switches=TenantKillSwitchConfig(**ks),
            rate_limits=TenantRateLimitConfig(**rl),
            roles=[TenantRoleModel(**r) for r in roles_raw],
            secret_redaction_enforced=ss.get("redaction_enforced", True),
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
