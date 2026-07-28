from __future__ import annotations

from erpguard.product.models import PolicyEvaluationRequestModel, PolicyEvaluationResultModel
from erpguard.product.platform_kill_switch import KillSwitchService

_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "operator": {"execute_real_read", "request_write_pilot"},
    "approver": {"approve_write_pilot", "activate_kill_switch", "view_audit_export"},
    "admin": {
        "execute_real_read", "request_write_pilot", "approve_write_pilot",
        "activate_kill_switch", "view_audit_export", "manage_tenant",
    },
}

_ACTION_REQUIRED_PERMISSIONS: dict[str, str] = {
    "execute_real_read": "execute_real_read",
    "request_write_pilot": "request_write_pilot",
    "approve_write_pilot": "approve_write_pilot",
    "activate_kill_switch": "activate_kill_switch",
    "view_audit_export": "view_audit_export",
    "manage_tenant": "manage_tenant",
}


class PlatformPolicyService:
    def __init__(self, session) -> None:
        self.session = session

    def evaluate(self, request: PolicyEvaluationRequestModel, tenant_id: str | None = None) -> PolicyEvaluationResultModel:
        violations: list[str] = []
        kill_switches_active: list[str] = []

        if tenant_id:
            ks_svc = KillSwitchService(self.session)
            kill_switches_active = ks_svc.active_switches_for_tenant(tenant_id)
            if kill_switches_active:
                violations.append(f"Kill switches active: {', '.join(kill_switches_active)}")

        actor_role = request.actor.get("role", "")
        required_permission = _ACTION_REQUIRED_PERMISSIONS.get(request.action)

        if required_permission is None:
            violations.append(f"Unknown action '{request.action}'.")
        elif actor_role not in _ROLE_PERMISSIONS:
            violations.append(f"Unknown role '{actor_role}'.")
        elif required_permission not in _ROLE_PERMISSIONS.get(actor_role, set()):
            violations.append(
                f"Role '{actor_role}' does not have permission '{required_permission}' required for action '{request.action}'."
            )

        allowed = len(violations) == 0

        reason = "Allowed." if allowed else f"Blocked: {'; '.join(violations)}"

        return PolicyEvaluationResultModel(
            allowed=allowed,
            actor=request.actor,
            action=request.action,
            resource=request.resource,
            reason=reason,
            violations=violations,
            kill_switches_active=kill_switches_active,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
        )
