from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_kill_switch_event,
    create_platform_audit_event,
    get_tenant,
    list_kill_switch_events_for_tenant,
    update_tenant_kill_switches,
)
from erpguard.product.models import KillSwitchEventModel, TenantKillSwitchConfig

_PLATFORM_GLOBAL_KILL_SWITCH = False
_RUNTIME_EXECUTION_KILL_SWITCH = False
_WRITE_PILOT_KILL_SWITCH = False

_VALID_SWITCH_NAMES = frozenset({
    "global_kill_switch",
    "runtime_execution_kill_switch",
    "write_pilot_kill_switch",
})


class KillSwitchService:
    def __init__(self, session) -> None:
        self.session = session

    def get_global_status(self) -> TenantKillSwitchConfig:
        return TenantKillSwitchConfig(
            global_kill_switch=_PLATFORM_GLOBAL_KILL_SWITCH,
            runtime_execution_kill_switch=_RUNTIME_EXECUTION_KILL_SWITCH,
            write_pilot_kill_switch=_WRITE_PILOT_KILL_SWITCH,
        )

    def activate(self, tenant_id: str, switch_name: str, activated_by: dict, reason: str) -> KillSwitchEventModel:
        if switch_name not in _VALID_SWITCH_NAMES:
            raise ValueError(f"Unknown kill switch '{switch_name}'. Valid: {sorted(_VALID_SWITCH_NAMES)}")

        tenant_row = get_tenant(self.session, tenant_id)
        if tenant_row is None:
            raise ObjectNotFoundError(f"Tenant '{tenant_id}' not found.")

        ks = json.loads(tenant_row.kill_switch_json)
        ks[switch_name] = True
        update_tenant_kill_switches(self.session, tenant_id, json.dumps(ks))

        ev = create_kill_switch_event(
            session=self.session,
            tenant_id=tenant_id,
            switch_name=switch_name,
            action="activate",
            activated_by_json=json.dumps(activated_by),
            reason=reason,
        )
        create_platform_audit_event(
            session=self.session,
            tenant_id=tenant_id,
            event_category="kill_switch",
            event_type=f"kill_switch.{switch_name}.activated",
            actor_json=json.dumps(activated_by),
            details_json=json.dumps({"switch_name": switch_name, "reason": reason}),
            severity="critical",
        )
        return self._ev_to_model(ev)

    def deactivate(self, tenant_id: str, switch_name: str, activated_by: dict, reason: str) -> KillSwitchEventModel:
        if switch_name not in _VALID_SWITCH_NAMES:
            raise ValueError(f"Unknown kill switch '{switch_name}'.")

        tenant_row = get_tenant(self.session, tenant_id)
        if tenant_row is None:
            raise ObjectNotFoundError(f"Tenant '{tenant_id}' not found.")

        ks = json.loads(tenant_row.kill_switch_json)
        ks[switch_name] = False
        update_tenant_kill_switches(self.session, tenant_id, json.dumps(ks))

        ev = create_kill_switch_event(
            session=self.session,
            tenant_id=tenant_id,
            switch_name=switch_name,
            action="deactivate",
            activated_by_json=json.dumps(activated_by),
            reason=reason,
        )
        return self._ev_to_model(ev)

    def is_any_active_for_tenant(self, tenant_id: str) -> bool:
        if _PLATFORM_GLOBAL_KILL_SWITCH or _RUNTIME_EXECUTION_KILL_SWITCH or _WRITE_PILOT_KILL_SWITCH:
            return True
        tenant_row = get_tenant(self.session, tenant_id)
        if tenant_row is None:
            return False
        ks = json.loads(tenant_row.kill_switch_json)
        return any(ks.values())

    def active_switches_for_tenant(self, tenant_id: str) -> list[str]:
        active = []
        if _PLATFORM_GLOBAL_KILL_SWITCH:
            active.append("platform_global_kill_switch")
        if _RUNTIME_EXECUTION_KILL_SWITCH:
            active.append("platform_runtime_execution_kill_switch")
        if _WRITE_PILOT_KILL_SWITCH:
            active.append("platform_write_pilot_kill_switch")
        tenant_row = get_tenant(self.session, tenant_id)
        if tenant_row:
            ks = json.loads(tenant_row.kill_switch_json)
            for k, v in ks.items():
                if v:
                    active.append(f"tenant_{k}")
        return active

    def list_events(self, tenant_id: str) -> list[KillSwitchEventModel]:
        rows = list_kill_switch_events_for_tenant(self.session, tenant_id)
        return [self._ev_to_model(r) for r in rows]

    @staticmethod
    def _ev_to_model(row) -> KillSwitchEventModel:
        return KillSwitchEventModel(
            event_id=row.id,
            tenant_id=row.tenant_id,
            switch_name=row.switch_name,
            action=row.action,
            activated_by=json.loads(row.activated_by_json),
            reason=row.reason,
            created_at=row.created_at.isoformat(),
        )
