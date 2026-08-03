"""Spec 92 Workstream A: MarginOpportunity -> GovernedRecommendation -> approval -> GovernedActionDraft -> ExecutionRun.

`MarginOpportunity` stays analytical evidence -- nothing here ever mutates
it. Approval reuses `ApprovalService`/`Approval` unchanged
(`erpguard/domain/execution/approval_service.py`); this module only adds
the app-level expiry check that model doesn't carry a field for (see
`settings.recommendation_approval_max_age_seconds`).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.config import settings
from erpguard.db.model_packages.decision_intelligence import MarginAnalysis
from erpguard.db.model_packages.execution import Approval
from erpguard.db.model_packages.recommendations import GovernedActionDraft, GovernedRecommendation
from erpguard.domain.deployment.service import SkillDeploymentService
from erpguard.domain.execution.permit_service import NoActiveSkillForProcess, PermitService
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.recommendations.state_machine import (
    ACTION_DRAFT_TRANSITIONS,
    RECOMMENDATION_TRANSITIONS,
    require_transition,
)
from erpguard.domain.recommendations.templates import UnknownActionTemplate, get_template
from erpguard.domain.recommendations.types import PricingScenarioInputs
from erpguard.domain.recommendations.validation import validate_pricing_scenario
from erpguard.application.opportunity.service import OpportunityEngineService, OpportunityNotFound


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class RecommendationNotFound(KeyError):
    pass


class ActionDraftNotFound(KeyError):
    pass


class RecommendationValidationError(ValueError):
    pass


class OpportunityBlocked(RecommendationValidationError):
    pass


class ApprovalRejected(RecommendationValidationError):
    pass


class NoActiveSkillForActionTemplate(RecommendationValidationError):
    pass


RECOMMENDATION_TYPES = {"product_price_review", "customer_discount_review", "cost_drift_review"}


class RecommendationService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, recommendation_id: str) -> GovernedRecommendation:
        row = (
            self.session.query(GovernedRecommendation)
            .filter_by(tenant_id=tenant_id, id=recommendation_id)
            .one_or_none()
        )
        if row is None:
            raise RecommendationNotFound(recommendation_id)
        return row

    def get(self, *, tenant_id: str, recommendation_id: str) -> GovernedRecommendation:
        return self._get(tenant_id=tenant_id, recommendation_id=recommendation_id)

    def create(
        self,
        *,
        tenant_id: str,
        opportunity_id: str,
        recommendation_type: str,
        title: str,
        selected_action_template: str,
        created_by: str,
    ) -> GovernedRecommendation:
        if recommendation_type not in RECOMMENDATION_TYPES:
            raise RecommendationValidationError(f"unknown_recommendation_type:{recommendation_type}")
        try:
            get_template(selected_action_template)
        except UnknownActionTemplate as exc:
            raise RecommendationValidationError(f"unknown_action_template:{selected_action_template}") from exc

        try:
            opportunity = OpportunityEngineService(self.session).get(tenant_id=tenant_id, opportunity_id=opportunity_id)
        except OpportunityNotFound as exc:
            raise RecommendationValidationError("margin_opportunity_not_found") from exc

        analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=opportunity.margin_analysis_id)
            .one_or_none()
        )
        if analysis is None or analysis.status == "blocked":
            raise OpportunityBlocked("margin_analysis_blocked_or_missing")

        content = {
            "margin_opportunity_content_hash": opportunity.content_hash,
            "recommendation_type": recommendation_type,
            "selected_action_template": selected_action_template,
            "affected_population": json.loads(opportunity.affected_population_json),
        }
        row = GovernedRecommendation(
            id=f"rec_{uuid4().hex}",
            tenant_id=tenant_id,
            margin_opportunity_id=opportunity.id,
            margin_analysis_id=opportunity.margin_analysis_id,
            snapshot_id=analysis.snapshot_id,
            recommendation_type=recommendation_type,
            title=title,
            business_rationale_json=_dump({"cause": opportunity.cause, "proposed_action": opportunity.proposed_action}),
            affected_population_json=opportunity.affected_population_json,
            estimated_impact_conservative=opportunity.impact_conservative,
            estimated_impact_base=opportunity.impact_base,
            estimated_impact_optimistic=opportunity.impact_optimistic,
            confidence_band=opportunity.confidence_band,
            risk_level=opportunity.risk_level,
            selected_action_template=selected_action_template,
            status="draft",
            source_content_hash=opportunity.content_hash,
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def submit(self, *, tenant_id: str, recommendation_id: str) -> GovernedRecommendation:
        row = self._get(tenant_id=tenant_id, recommendation_id=recommendation_id)
        require_transition(RECOMMENDATION_TRANSITIONS, current=row.status, target="submitted")
        row.status = "submitted"
        row.submitted_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    @staticmethod
    def approval_scope(recommendation: GovernedRecommendation) -> str:
        return f"recommendation:{recommendation.id}:approve:{recommendation.content_hash}"

    def approve(
        self, *, tenant_id: str, recommendation_id: str, approval_id: str, approver_actor_id: str
    ) -> GovernedRecommendation:
        row = self._get(tenant_id=tenant_id, recommendation_id=recommendation_id)
        require_transition(RECOMMENDATION_TRANSITIONS, current=row.status, target="approved")

        approval = self.session.query(Approval).filter_by(tenant_id=tenant_id, id=approval_id).one_or_none()
        if approval is None:
            raise ApprovalRejected("approval_not_found")
        if approval.used_at is not None:
            raise ApprovalRejected("approval_already_used")
        if approval.actor_id == row.created_by:
            raise ApprovalRejected("recommendation_creator_cannot_approve")
        if approval.actor_id != approver_actor_id:
            raise ApprovalRejected("approval_actor_mismatch")
        if approval.scope != self.approval_scope(row):
            raise ApprovalRejected("approval_scope_mismatch")
        age = _utc_now() - approval.created_at.replace(tzinfo=timezone.utc if approval.created_at.tzinfo is None else approval.created_at.tzinfo)
        if age > timedelta(seconds=settings.recommendation_approval_max_age_seconds):
            raise ApprovalRejected("approval_expired")

        approval.used_at = _utc_now()
        approval.used_by_run_id = row.id
        row.status = "approved"
        row.approved_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def reject(self, *, tenant_id: str, recommendation_id: str) -> GovernedRecommendation:
        row = self._get(tenant_id=tenant_id, recommendation_id=recommendation_id)
        require_transition(RECOMMENDATION_TRANSITIONS, current=row.status, target="rejected")
        row.status = "rejected"
        self.session.commit()
        self.session.refresh(row)
        return row

    def _get_draft(self, *, tenant_id: str, action_draft_id: str) -> GovernedActionDraft:
        row = (
            self.session.query(GovernedActionDraft)
            .filter_by(tenant_id=tenant_id, id=action_draft_id)
            .one_or_none()
        )
        if row is None:
            raise ActionDraftNotFound(action_draft_id)
        return row

    def get_action_draft(self, *, tenant_id: str, action_draft_id: str) -> GovernedActionDraft:
        return self._get_draft(tenant_id=tenant_id, action_draft_id=action_draft_id)

    def create_action_draft(
        self,
        *,
        tenant_id: str,
        recommendation_id: str,
        process_key: str,
        connection_id: str | None,
        pricing_inputs: PricingScenarioInputs | None,
        created_by: str,
    ) -> GovernedActionDraft:
        """`process_key` names the governed process whose active `SkillPackage`
        (Phase 19's `SkillDeploymentService.get_active`) will execute this
        draft -- the same process a candidate/proof/skill-package chain was
        compiled for, not derived from the opportunity itself."""

        recommendation = self._get(tenant_id=tenant_id, recommendation_id=recommendation_id)
        if recommendation.status != "approved":
            raise RecommendationValidationError(f"recommendation_not_approved:{recommendation.status}")

        template = get_template(recommendation.selected_action_template)

        arguments: dict = {}
        constraints: dict = {"required_inputs_satisfied": True}
        capability = template.capability or ""
        connector_id = template.connector_id or ""

        if template.execution_classification == "executable":
            if pricing_inputs is None:
                raise RecommendationValidationError("pricing_inputs_required_for_executable_template")
            issues = validate_pricing_scenario(pricing_inputs)
            if issues:
                raise RecommendationValidationError(f"pricing_scenario_validation_failed:{','.join(issues)}")
            client_reference = f"GERP-{recommendation.id}"
            arguments = {
                "partner_id": pricing_inputs.partner_id,
                "client_reference": client_reference,
                "company_id": pricing_inputs.company_id,
                "currency_id": pricing_inputs.currency_id,
                "pricelist_id": pricing_inputs.pricelist_id,
                "lines": [
                    {
                        "product_id": line.product_id,
                        "quantity": line.quantity,
                        "price_unit": str(line.proposed_unit_price),
                        "cost_reference": str(line.cost_reference),
                        "minimum_margin_percent": str(line.minimum_margin_percent),
                    }
                    for line in pricing_inputs.lines
                ],
            }
            constraints = {
                "company_id": pricing_inputs.company_id,
                "currency_id": pricing_inputs.currency_id,
                "pricelist_id": pricing_inputs.pricelist_id,
                "recommendation_id": recommendation.id,
                "pricing_evidence": [line.model_dump(mode="json") for line in pricing_inputs.lines],
            }

        content = {
            "recommendation_id": recommendation.id,
            "recommendation_content_hash": recommendation.content_hash,
            "action_template": template.name,
            "action_template_version": template.version,
            "arguments": arguments,
        }
        row = GovernedActionDraft(
            id=f"actdraft_{uuid4().hex}",
            tenant_id=tenant_id,
            recommendation_id=recommendation.id,
            action_template=template.name,
            action_template_version=template.version,
            connector_id=connector_id,
            process_key=process_key,
            capability=capability,
            connection_id=connection_id,
            arguments_json=_dump(arguments),
            constraints_json=_dump(constraints),
            required_inputs_json=_dump([]),
            preflight_spec_json=_dump({"checks": ["margin_floor", "line_bounds", "total_ceiling"]}),
            postcondition_spec_json=_dump({"checks": ["state_draft", "no_confirmation"]}),
            compensation_spec_json=_dump({"strategy": "manual_cancellation_or_archival"}),
            execution_classification=template.execution_classification,
            status="draft",
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def validate_action_draft(self, *, tenant_id: str, action_draft_id: str) -> GovernedActionDraft:
        row = self._get_draft(tenant_id=tenant_id, action_draft_id=action_draft_id)
        require_transition(ACTION_DRAFT_TRANSITIONS, current=row.status, target="validated")
        row.status = "validated"
        row.validated_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def mark_ready_for_run(self, *, tenant_id: str, action_draft_id: str) -> GovernedActionDraft:
        row = self._get_draft(tenant_id=tenant_id, action_draft_id=action_draft_id)
        require_transition(ACTION_DRAFT_TRANSITIONS, current=row.status, target="ready_for_run")
        row.status = "ready_for_run"
        self.session.commit()
        self.session.refresh(row)
        return row

    def invalidate_action_draft(self, *, tenant_id: str, action_draft_id: str) -> GovernedActionDraft:
        row = self._get_draft(tenant_id=tenant_id, action_draft_id=action_draft_id)
        require_transition(ACTION_DRAFT_TRANSITIONS, current=row.status, target="invalidated")
        row.status = "invalidated"
        row.invalidated_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def convert_to_run(
        self,
        *,
        tenant_id: str,
        action_draft_id: str,
        actor_id: str,
        idempotency_key: str,
        routing_context: dict | None = None,
    ) -> GovernedActionDraft:
        """`routing_context` (Spec 92 Sec 9.5) routes this run through the
        operational canary router instead of always resolving the current
        stable active package -- optional so existing callers that never
        pass it keep the pre-Workstream-B direct-to-stable behavior."""

        row = self._get_draft(tenant_id=tenant_id, action_draft_id=action_draft_id)
        if row.status == "converted":
            return row
        require_transition(ACTION_DRAFT_TRANSITIONS, current=row.status, target="converted")
        if row.execution_classification != "executable":
            raise RecommendationValidationError("action_draft_not_executable")
        if row.connection_id is None:
            raise RecommendationValidationError("action_draft_missing_connection")

        permit_service = PermitService(self.session)
        if routing_context is not None:
            try:
                run = permit_service.plan(
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    connection_id=row.connection_id,
                    process_key=row.process_key,
                    routing_context=routing_context,
                    capability=row.capability,
                    idempotency_key=idempotency_key,
                    capability_payload=json.loads(row.arguments_json),
                )
            except NoActiveSkillForProcess as exc:
                raise NoActiveSkillForActionTemplate(f"no_active_skill_for_process:{row.process_key}") from exc
        else:
            skill_package = SkillDeploymentService(self.session).get_active(
                tenant_id=tenant_id, process_key=row.process_key
            )
            if skill_package is None:
                raise NoActiveSkillForActionTemplate(f"no_active_skill_for_process:{row.process_key}")

            run = permit_service.plan(
                tenant_id=tenant_id,
                actor_id=actor_id,
                connection_id=row.connection_id,
                skill_package_id=skill_package.id,
                capability=row.capability,
                idempotency_key=idempotency_key,
                capability_payload=json.loads(row.arguments_json),
            )
        row.status = "converted"
        row.converted_run_id = run.id

        # One commit for both status flips -- a crash between them used to
        # leave a real ExecutionRun with the draft "converted" but the
        # recommendation still "approved", which a retry (new idempotency
        # key) could plan a second run against.
        recommendation = self._get(tenant_id=tenant_id, recommendation_id=row.recommendation_id)
        if recommendation.status == "approved":
            recommendation.status = "converted"
            recommendation.converted_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row
