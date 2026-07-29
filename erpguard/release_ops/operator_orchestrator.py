from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_operator_session_event,
    get_operator_session,
    update_operator_session,
)
from erpguard.release_ops.operator_flow_state import (
    BLOCKING_STEPS,
    SAFE_READONLY_BOUNDARY,
    is_before_or_at,
    next_step,
)


class OperatorOrchestrator:
    def __init__(self, session) -> None:
        self.session = session

    # ── Public API ─────────────────────────────────────────────────────────

    def run_next(self, session_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        if row.status == "completed":
            return self._session_dict(row, message="Session already completed.")
        if row.current_step == "completed":
            update_operator_session(self.session, session_id, status="completed")
            row = get_operator_session(self.session, session_id)
            return self._session_dict(row, message="All steps completed.")

        step = row.current_step
        if step in BLOCKING_STEPS:
            return self._session_dict(row, message=f"Step '{step}' requires operator input. Call the appropriate select-* endpoint first.")

        result = self._execute_step(session_id, step, json.loads(row.known_ids_json))
        return result

    def run_safe_readonly_path(self, session_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")

        steps_executed: list[str] = []
        errors: list[str] = []

        for _ in range(20):
            row = get_operator_session(self.session, session_id)
            if row is None:
                break
            step = row.current_step
            if step == "completed" or row.status == "completed":
                break
            if not is_before_or_at(step, SAFE_READONLY_BOUNDARY):
                break
            if step in BLOCKING_STEPS:
                errors.append(f"Blocked at '{step}': operator input required.")
                break

            result = self._execute_step(session_id, step, json.loads(row.known_ids_json))
            steps_executed.append(step)
            if result.get("step_status") == "error":
                errors.append(f"{step}: {result.get('message', 'error')}")
                break

        row = get_operator_session(self.session, session_id)
        return {
            **self._session_dict(row),
            "steps_executed": steps_executed,
            "errors": errors,
        }

    # ── Step dispatcher ────────────────────────────────────────────────────

    def _execute_step(self, session_id: str, step: str, known_ids: dict) -> dict:
        handler = {
            "awaiting_tenant": self._step_awaiting_tenant,
            "run_diagnosis": self._step_run_diagnosis,
            "run_business_analysis": self._step_run_business_analysis,
            "select_opportunity": self._step_select_opportunity,
            "create_draft": self._step_create_draft,
            "review_draft": self._step_review_draft,
            "compile_skill": self._step_compile_skill,
            "run_dry_run_proof": self._step_run_dry_run_proof,
            "request_approval": self._step_request_approval,
            "submit_decision": self._step_submit_decision,
            "run_activation_gate": self._step_run_activation_gate,
            "run_live_read": self._step_run_live_read,
            "run_write_readiness": self._step_run_write_readiness,
            "optional_r1_write_pilot": self._step_optional_r1_write_pilot,
        }.get(step)

        if handler is None:
            return self._record_and_advance(session_id, step, known_ids, {}, status="skipped", message=f"No handler for step '{step}', skipping.")

        try:
            new_ids, message = handler(known_ids)
            return self._record_and_advance(session_id, step, known_ids, new_ids, status="ok", message=message)
        except Exception as exc:
            return self._record_error(session_id, step, known_ids, str(exc))

    # ── Step implementations ───────────────────────────────────────────────

    def _step_awaiting_tenant(self, known_ids: dict) -> tuple[dict, str]:
        if known_ids.get("tenant_id"):
            return {}, f"Tenant already set: {known_ids['tenant_id']}"
        from erpguard.release_ops.platform_tenant import TenantService
        tenant = TenantService(self.session).create(name="Operator Flow Tenant", environment="staging")
        return {"tenant_id": tenant.tenant_id}, f"Auto-created tenant: {tenant.tenant_id}"

    def _step_run_diagnosis(self, known_ids: dict) -> tuple[dict, str]:
        connection_id = known_ids.get("connection_id")
        if not connection_id:
            return {}, "No connection set — skipping diagnosis."
        from erpguard.db.repositories import get_connection
        from erpguard.adapters.odoo.config import OdooConfig
        from erpguard.adapters.odoo.readonly_client import build_readonly_client
        from erpguard.adapters.odoo.diagnosis import OdooDiagnosisService
        connection = get_connection(self.session, connection_id)
        if connection is None:
            return {}, f"Connection '{connection_id}' not found — skipping diagnosis."
        config = OdooConfig.model_validate(json.loads(connection.config_json))
        client = build_readonly_client(config)
        svc = OdooDiagnosisService(client=client, config=config)
        result = svc.run(include_samples=False, sample_limits={})
        return {"diagnosis_status": result.get("status", "ok")}, f"Diagnosis: {result.get('status', 'ok')}"

    def _step_run_business_analysis(self, known_ids: dict) -> tuple[dict, str]:
        connection_id = known_ids.get("connection_id")
        if not connection_id:
            return {}, "No connection set — skipping business analysis."
        from erpguard.db.repositories import get_connection
        from erpguard.adapters.odoo.config import OdooConfig
        from erpguard.canonical.enums import ERPType
        from erpguard.product.models import BusinessAnalysisRequest
        from erpguard.release_ops.services import BusinessAnalysisService
        connection = get_connection(self.session, connection_id)
        if connection is None or connection.erp_type != ERPType.ODOO.value:
            return {}, f"Connection '{connection_id}' not found or not Odoo — skipping."
        config = OdooConfig.model_validate(json.loads(connection.config_json))
        request = BusinessAnalysisRequest(include_samples=True, max_opportunities=5)
        result = BusinessAnalysisService(self.session, connection, config).analyze(request)
        opportunity_ids = [o.opportunity_id for o in result.opportunities]
        new_ids: dict = {
            "snapshot_id": result.snapshot_id,
            "scan_id": result.scan_id,
            "opportunity_ids": opportunity_ids,
        }
        if opportunity_ids:
            new_ids["opportunity_id"] = opportunity_ids[0]
        return new_ids, f"Business analysis complete. {len(opportunity_ids)} opportunities found."

    def _step_select_opportunity(self, known_ids: dict) -> tuple[dict, str]:
        opp_id = known_ids.get("opportunity_id")
        if opp_id:
            return {}, f"Opportunity already selected: {opp_id}"
        opp_ids = known_ids.get("opportunity_ids", [])
        if not opp_ids:
            return {}, "No opportunities available — skipping."
        return {"opportunity_id": opp_ids[0]}, f"Auto-selected opportunity: {opp_ids[0]}"

    def _step_create_draft(self, known_ids: dict) -> tuple[dict, str]:
        opportunity_id = known_ids.get("opportunity_id")
        if not opportunity_id:
            raise ValueError("opportunity_id required for create_draft step.")
        connection_id = known_ids.get("connection_id")
        from erpguard.db.repositories import get_connection, get_opportunity
        from erpguard.adapters.odoo.config import OdooConfig
        from erpguard.canonical.enums import ERPType
        from erpguard.release_ops.services import BusinessAnalysisService
        opp = get_opportunity(self.session, opportunity_id)
        if opp is None:
            raise ValueError(f"Opportunity '{opportunity_id}' not found.")
        cid = connection_id or opp.connection_id
        connection = get_connection(self.session, cid)
        if connection is None or connection.erp_type != ERPType.ODOO.value:
            raise ValueError(f"Connection '{cid}' not found or not Odoo.")
        config = OdooConfig.model_validate(json.loads(connection.config_json))
        draft = BusinessAnalysisService(self.session, connection, config).draft(opportunity_id)
        return {"draft_id": draft.draft_id}, f"Draft created: {draft.draft_id}"

    def _step_review_draft(self, known_ids: dict) -> tuple[dict, str]:
        draft_id = known_ids.get("draft_id")
        if not draft_id:
            raise ValueError("draft_id required for review_draft step.")
        from erpguard.release_ops.draft_review import DraftReviewService
        review = DraftReviewService(self.session).get_or_create(draft_id)
        return {"review_id": review.review_id}, f"Draft reviewed: {review.review_id} ({review.status})"

    def _step_compile_skill(self, known_ids: dict) -> tuple[dict, str]:
        review_id = known_ids.get("review_id")
        if not review_id:
            raise ValueError("review_id required for compile_skill step.")
        from erpguard.release_ops.skill_package_builder import SkillPackageBuilder
        compiled = SkillPackageBuilder(self.session).build(review_id)
        return {"skill_id": compiled.skill_id, "version_id": compiled.version_id}, f"Skill compiled: {compiled.skill_id}"

    def _step_run_dry_run_proof(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for run_dry_run_proof step.")
        from erpguard.release_ops.dry_run_proof import DryRunProofService
        proof = DryRunProofService(self.session).run(skill_id)
        return {"proof_id": proof.proof_id}, f"Dry-run proof: {proof.status} ({proof.cases_passed}/{proof.cases_total} passed)"

    def _step_request_approval(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for request_approval step.")
        from erpguard.release_ops.approval_request import ApprovalRequestService
        req = ApprovalRequestService(self.session).create(
            skill_id=skill_id,
            requested_by={"type": "operator_flow", "id": "auto", "display_name": "Operator Flow"},
            reason="Auto-submitted by operator flow.",
        )
        return {"approval_request_id": req.request_id}, f"Approval request: {req.request_id} ({req.status})"

    def _step_submit_decision(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for submit_decision step.")
        from erpguard.release_ops.approval_decision import ApprovalDecisionService
        decision = ApprovalDecisionService(self.session).decide(
            skill_id=skill_id,
            decided_by={"type": "operator_flow", "id": "auto", "display_name": "Operator Flow"},
            decision="approve",
            reason="Auto-approved by operator flow for governance state only.",
        )
        return {"approval_decision_id": decision.decision_id}, f"Decision: {decision.decision} ({decision.decision_id})"

    def _step_run_activation_gate(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for run_activation_gate step.")
        from erpguard.release_ops.activation_gate import ActivationGateService
        gate = ActivationGateService(self.session).evaluate(skill_id)
        return {"activation_gate_id": gate.gate_id}, f"Activation gate: {gate.gate_status} ({gate.gate_id})"

    def _step_run_live_read(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for run_live_read step.")
        from erpguard.release_ops.live_read_request import LiveReadRequestService
        from erpguard.release_ops.live_read_runtime import LiveReadRuntimeService
        lr_req, _ = LiveReadRequestService(self.session).create(
            skill_id=skill_id,
            requested_by={"type": "operator_flow", "id": "auto", "display_name": "Operator Flow"},
            inputs={"live_read": True},
        )
        run = LiveReadRuntimeService(self.session).execute(lr_req.request_id)
        return {
            "live_read_request_id": lr_req.request_id,
            "live_read_run_id": run.run_id,
        }, f"Live read: {run.status} ({run.real_read_count} read(s), {run.blocked_write_count} write(s) blocked)"

    def _step_run_write_readiness(self, known_ids: dict) -> tuple[dict, str]:
        skill_id = known_ids.get("skill_id")
        if not skill_id:
            raise ValueError("skill_id required for run_write_readiness step.")
        from erpguard.release_ops.write_readiness_assessment import WriteReadinessAssessmentService
        assessment = WriteReadinessAssessmentService(self.session).run(skill_id)
        return {"assessment_id": assessment.assessment_id}, f"Write readiness: {assessment.overall_risk_level} (can_execute_real_writes={assessment.can_execute_real_writes})"

    def _step_optional_r1_write_pilot(self, known_ids: dict) -> tuple[dict, str]:
        return {}, "R1 write pilot is optional and blocked by default (ALLOW_R1_REAL_WRITE_PILOT=false). Use the write pilot endpoint directly to opt-in."

    # ── Helpers ────────────────────────────────────────────────────────────

    def _record_and_advance(
        self,
        session_id: str,
        step: str,
        known_ids: dict,
        new_ids: dict,
        status: str,
        message: str,
    ) -> dict:
        merged = {**known_ids, **new_ids}
        nxt = next_step(step) or "completed"
        update_operator_session(
            self.session,
            session_id,
            current_step=nxt,
            known_ids_json=json.dumps(merged),
            status="completed" if nxt == "completed" else "active",
        )
        create_operator_session_event(
            self.session,
            session_id=session_id,
            step=step,
            status=status,
            detail_json=json.dumps({"message": message, "new_ids": new_ids}),
        )
        row = get_operator_session(self.session, session_id)
        return {**self._session_dict(row), "step_status": status, "message": message}

    def _record_error(self, session_id: str, step: str, known_ids: dict, error: str) -> dict:
        create_operator_session_event(
            self.session,
            session_id=session_id,
            step=step,
            status="error",
            detail_json=json.dumps({"error": error}),
        )
        row = get_operator_session(self.session, session_id)
        return {**self._session_dict(row), "step_status": "error", "message": error}

    @staticmethod
    def _session_dict(row, message: str = "") -> dict:
        return {
            "session_id": row.id,
            "tenant_id": row.tenant_id,
            "connection_id": row.connection_id,
            "current_step": row.current_step,
            "status": row.status,
            "known_ids": json.loads(row.known_ids_json),
            "message": message,
        }
