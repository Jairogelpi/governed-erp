from __future__ import annotations

from erpguard.product.operator_orchestrator import OperatorOrchestrator
from erpguard.product.operator_session import OperatorSessionService
from erpguard.product.platform_tenant import TenantService
from erpguard.product.release_readiness import ReleaseReadinessService


class OperatorSmokeService:
    def __init__(self, session) -> None:
        self.session = session

    def run(self) -> dict:
        checks: list[dict] = []

        # 1 — DB + readiness
        try:
            readiness = ReleaseReadinessService(self.session).report()
            checks.append(_ok("release_readiness", f"Readiness score: {readiness['readiness_score']}%"))
        except Exception as exc:
            checks.append(_fail("release_readiness", str(exc)))

        # 2 — Tenant creation
        tenant_id = None
        try:
            tenant = TenantService(self.session).create(name="Smoke Test Tenant", environment="staging")
            tenant_id = tenant.tenant_id
            checks.append(_ok("tenant_creation", f"Tenant created: {tenant_id}"))
        except Exception as exc:
            checks.append(_fail("tenant_creation", str(exc)))

        # 3 — Operator session creation
        session_id = None
        try:
            svc = OperatorSessionService(self.session)
            op_session = svc.create()
            session_id = op_session["session_id"]
            checks.append(_ok("operator_session_creation", f"Session created: {session_id} at {op_session['current_step']}"))
        except Exception as exc:
            checks.append(_fail("operator_session_creation", str(exc)))

        # 4 — Advance operator flow (awaiting_tenant step)
        try:
            orch = OperatorOrchestrator(self.session)
            result = orch.run_next(session_id)
            checks.append(_ok("operator_flow_advance", f"Step advanced: {result.get('message', 'ok')} → now at {result.get('current_step')}"))
        except Exception as exc:
            checks.append(_fail("operator_flow_advance", str(exc)))

        # 5 — Tenant select via session
        if tenant_id and session_id:
            try:
                svc = OperatorSessionService(self.session)
                updated = svc.select_tenant(session_id, tenant_id)
                checks.append(_ok("tenant_selection", f"Tenant set on session. Step: {updated['current_step']}"))
            except Exception as exc:
                checks.append(_fail("tenant_selection", str(exc)))

        # 6 — Safety boundaries constant check
        try:
            from erpguard.product.release_readiness import _SAFETY_BOUNDARIES
            all_false = all(not v for v in _SAFETY_BOUNDARIES.values())
            if all_false:
                checks.append(_ok("safety_boundaries", "All write flags are false. Generic/R3R4 writes locked."))
            else:
                checks.append(_fail("safety_boundaries", f"Unexpected flag enabled: {_SAFETY_BOUNDARIES}"))
        except Exception as exc:
            checks.append(_fail("safety_boundaries", str(exc)))

        # 7 — R2 policy service importable
        try:
            from erpguard.product.r2_write_policy import R2WritePilotPolicyService, _ALLOW_R2_REAL_WRITE_PILOT
            assert not _ALLOW_R2_REAL_WRITE_PILOT
            checks.append(_ok("r2_pilot_flag_default_off", "ALLOW_R2_REAL_WRITE_PILOT=false confirmed."))
        except Exception as exc:
            checks.append(_fail("r2_pilot_flag_default_off", str(exc)))

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        overall = "passed" if passed == total else "partial" if passed >= total * 0.8 else "failed"

        return {
            "smoke_status": overall,
            "checks_passed": passed,
            "checks_total": total,
            "checks": checks,
            "safety_invariants": {
                "can_execute_real_writes": False,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
            },
        }


def _ok(name: str, detail: str) -> dict:
    return {"name": name, "passed": True, "detail": detail}


def _fail(name: str, detail: str) -> dict:
    return {"name": name, "passed": False, "detail": detail}
