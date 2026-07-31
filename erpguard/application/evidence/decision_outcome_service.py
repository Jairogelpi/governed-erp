"""Spec 92 Workstream D: `DecisionOutcomeEvidenceService` gathers every
resource in the decision-to-outcome lifecycle for one `GovernedRecommendation`
and seals them into one immutable, hash-chained
`DecisionOutcomeEvidenceBundle` (Sec 11).

Canary routing is genuinely optional in this system (Sec 9.5 point 4: no
routing context means the stable active package runs, no `CanaryPolicy`
involved at all) -- so canary policy/routing-decision/safety-incident
references never block a bundle from becoming `complete`. Everything else
in the manifest (Sec 11.2) is required.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.canary import CanaryPolicy, CanaryRoutingDecision, CanarySafetyIncident
from erpguard.db.model_packages.decision_intelligence import AnalyticalSnapshot, DataQualityReport, MarginAnalysis
from erpguard.db.model_packages.decision_outcome_evidence import DecisionOutcomeEvidenceBundle
from erpguard.db.model_packages.execution import Approval, ExecutionRun
from erpguard.db.model_packages.opportunity import MarginOpportunity
from erpguard.db.model_packages.outcomes import OutcomeMeasurementPlan, OutcomeObservation, RealizedOutcomeReport
from erpguard.db.model_packages.recommendations import GovernedActionDraft, GovernedRecommendation
from erpguard.db.model_packages.skill_deployment import SkillDeploymentEvent
from erpguard.domain.evidence.decision_outcome_bundle import (
    ResourceReference,
    chain_hash,
    contains_secret_like_field,
    content_hash as compute_content_hash,
    manifest_hash,
)
from erpguard.domain.execution.permit_service import EvidenceNotAvailable, PermitService, RunTampered
from erpguard.domain.processes.candidate_integrity import stable_digest

_PLAN_TERMINAL_STATUSES = {"evaluated", "blocked", "inconclusive"}
_RUN_TERMINAL_STATUSES = {"executed", "succeeded", "blocked", "failed", "unknown"}
_OBSERVATION_SOURCE_TO_REALITY = {
    "live_odoo_read": "staging_live",
    "fixture": "fixture",
    "manual_import": "manual",
}

# Manifest resource types required for a bundle to reach `complete`.
_REQUIRED_TYPES = (
    "analytical_snapshot", "data_quality_report", "margin_analysis", "margin_opportunity",
    "governed_recommendation", "recommendation_approval", "action_draft", "action_validation",
    "execution_run", "execution_approval", "execution_permit", "postcondition_result",
    "execution_evidence_pack", "measurement_plan", "outcome_observation", "realized_outcome_report",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _row_hash(row, fields: list[str]) -> str:
    values = {}
    for field in fields:
        value = getattr(row, field)
        values[field] = value.isoformat() if isinstance(value, datetime) else value
    return stable_digest(values)


class EvidenceBundleNotFound(KeyError):
    pass


class EvidenceSealValidationError(ValueError):
    pass


class EvidenceIntegrityFailed(ValueError):
    pass


class DecisionOutcomeEvidenceService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, bundle_id: str) -> DecisionOutcomeEvidenceBundle:
        row = (
            self.session.query(DecisionOutcomeEvidenceBundle)
            .filter_by(tenant_id=tenant_id, id=bundle_id)
            .one_or_none()
        )
        if row is None:
            raise EvidenceBundleNotFound(bundle_id)
        return row

    def get(self, *, tenant_id: str, bundle_id: str) -> DecisionOutcomeEvidenceBundle:
        return self._get(tenant_id=tenant_id, bundle_id=bundle_id)

    # -- gathering ---------------------------------------------------------

    def _gather(self, *, tenant_id: str, recommendation_id: str, measurement_plan_id: str | None):
        references: list[ResourceReference] = []
        missing: list[str] = []
        unresolved_incident_ids: list[str] = []

        def add(resource_type, resource_id, content_hash_value, created_at, reality_label):
            references.append(
                ResourceReference(
                    resource_type=resource_type, resource_id=resource_id, content_hash=content_hash_value,
                    created_at=created_at, tenant_id=tenant_id, reality_label=reality_label,
                )
            )

        recommendation = (
            self.session.query(GovernedRecommendation)
            .filter_by(tenant_id=tenant_id, id=recommendation_id)
            .one_or_none()
        )
        if recommendation is None:
            missing.append("governed_recommendation")
            return references, missing, unresolved_incident_ids, None
        add("governed_recommendation", recommendation.id, recommendation.content_hash, _iso(recommendation.created_at), "derived")

        snapshot = (
            self.session.query(AnalyticalSnapshot)
            .filter_by(tenant_id=tenant_id, id=recommendation.snapshot_id)
            .one_or_none()
        )
        if snapshot is None:
            missing.append("analytical_snapshot")
        else:
            add("analytical_snapshot", snapshot.id, snapshot.source_hash, _iso(snapshot.created_at), "live")

        dq_report = (
            self.session.query(DataQualityReport)
            .filter_by(tenant_id=tenant_id, snapshot_id=recommendation.snapshot_id)
            .order_by(DataQualityReport.created_at.desc())
            .first()
        )
        if dq_report is None:
            missing.append("data_quality_report")
        else:
            add("data_quality_report", dq_report.id, dq_report.content_hash, _iso(dq_report.created_at), "derived")

        analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=recommendation.margin_analysis_id)
            .one_or_none()
        )
        if analysis is None:
            missing.append("margin_analysis")
        else:
            add("margin_analysis", analysis.id, analysis.content_hash, _iso(analysis.created_at), "derived")

        opportunity = (
            self.session.query(MarginOpportunity)
            .filter_by(tenant_id=tenant_id, id=recommendation.margin_opportunity_id)
            .one_or_none()
        )
        if opportunity is None:
            missing.append("margin_opportunity")
        else:
            add("margin_opportunity", opportunity.id, opportunity.content_hash, _iso(opportunity.created_at), "derived")

        approval_scope = f"recommendation:{recommendation.id}:approve:{recommendation.content_hash}"
        approval = (
            self.session.query(Approval)
            .filter_by(tenant_id=tenant_id, used_by_run_id=recommendation.id, scope=approval_scope)
            .one_or_none()
        )
        if approval is None:
            missing.append("recommendation_approval")
        else:
            add(
                "recommendation_approval", approval.id,
                _row_hash(approval, ["actor_id", "scope", "used_at"]), _iso(approval.created_at), "manual",
            )

        action_draft = (
            self.session.query(GovernedActionDraft)
            .filter_by(tenant_id=tenant_id, recommendation_id=recommendation.id)
            .order_by(GovernedActionDraft.created_at.desc())
            .first()
        )
        if action_draft is None:
            missing.append("action_draft")
            missing.append("action_validation")
        else:
            add("action_draft", action_draft.id, action_draft.content_hash, _iso(action_draft.created_at), "derived")
            if action_draft.validated_at is None:
                missing.append("action_validation")
            else:
                add(
                    "action_validation", action_draft.id,
                    _row_hash(action_draft, ["status", "content_hash"]), _iso(action_draft.validated_at), "derived",
                )

        run: ExecutionRun | None = None
        if action_draft is not None and action_draft.converted_run_id is not None:
            run = (
                self.session.query(ExecutionRun)
                .filter_by(tenant_id=tenant_id, id=action_draft.converted_run_id)
                .one_or_none()
            )
        if run is None:
            for resource_type in (
                "execution_run", "execution_approval", "execution_permit",
                "postcondition_result", "execution_evidence_pack",
            ):
                missing.append(resource_type)
        else:
            add(
                "execution_run", run.id,
                _row_hash(run, ["operation_hash", "native_plan_hash", "state_snapshot_hash", "status"]),
                _iso(run.created_at), "staging_live",
            )
            run_approval_ids = json.loads(run.approval_ids_json or "[]")
            run_approvals = (
                self.session.query(Approval).filter(Approval.id.in_(run_approval_ids)).all()
                if run_approval_ids
                else []
            )
            if not run_approvals:
                missing.append("execution_approval")
            else:
                for run_approval in run_approvals:
                    add(
                        "execution_approval", run_approval.id,
                        _row_hash(run_approval, ["actor_id", "scope", "used_at"]),
                        _iso(run_approval.created_at), "manual",
                    )
            if run.signature:
                add(
                    "execution_permit", run.id,
                    _row_hash(run, ["signature", "approval_ids_json", "capability_allowlist_json", "expires_at"]),
                    _iso(run.approved_at), "derived",
                )
            else:
                missing.append("execution_permit")

            if run.status in _RUN_TERMINAL_STATUSES:
                add(
                    "postcondition_result", run.id, _row_hash(run, ["verification_result_json", "status"]),
                    _iso(run.executed_at), "staging_live",
                )
                try:
                    evidence = PermitService(self.session).get_evidence(tenant_id=tenant_id, run_id=run.id)
                    add(
                        "execution_evidence_pack", run.id, evidence["sealed_digest"],
                        _iso(run.executed_at), "staging_live",
                    )
                except EvidenceNotAvailable:
                    missing.append("execution_evidence_pack")
                except RunTampered as exc:
                    raise EvidenceIntegrityFailed(f"execution_evidence_pack_tampered:{run.id}") from exc
            else:
                missing.append("postcondition_result")
                missing.append("execution_evidence_pack")

            if run.canary_policy_id:
                policy = (
                    self.session.query(CanaryPolicy)
                    .filter_by(tenant_id=tenant_id, id=run.canary_policy_id)
                    .one_or_none()
                )
                if policy is not None:
                    add("canary_policy", policy.id, policy.content_hash, _iso(policy.created_at), "derived")
            if run.routing_decision_id:
                decision = (
                    self.session.query(CanaryRoutingDecision)
                    .filter_by(tenant_id=tenant_id, id=run.routing_decision_id)
                    .one_or_none()
                )
                if decision is not None:
                    add(
                        "canary_routing_decision", decision.id,
                        _row_hash(decision, ["routing_context_hash", "bucket", "selected_lane", "selection_reason"]),
                        _iso(decision.created_at), "derived",
                    )
            if run.canary_policy_id:
                incidents = (
                    self.session.query(CanarySafetyIncident)
                    .filter_by(tenant_id=tenant_id, canary_policy_id=run.canary_policy_id)
                    .all()
                )
                for incident in incidents:
                    add(
                        "canary_safety_incident", incident.id,
                        _row_hash(incident, ["incident_type", "severity", "resolved_at"]),
                        _iso(incident.created_at), "derived",
                    )
                    if incident.resolved_at is None:
                        unresolved_incident_ids.append(incident.id)

            events = (
                self.session.query(SkillDeploymentEvent)
                .filter_by(tenant_id=tenant_id, skill_package_id=run.skill_package_id)
                .order_by(SkillDeploymentEvent.created_at.asc())
                .all()
            )
            for deployment_event in events:
                add(
                    "audit_event", deployment_event.id,
                    _row_hash(deployment_event, ["event_type", "from_status", "to_status"]),
                    _iso(deployment_event.created_at), "derived",
                )

        plan = None
        if measurement_plan_id is not None:
            plan = (
                self.session.query(OutcomeMeasurementPlan)
                .filter_by(tenant_id=tenant_id, id=measurement_plan_id, recommendation_id=recommendation.id)
                .one_or_none()
            )
        else:
            plan = (
                self.session.query(OutcomeMeasurementPlan)
                .filter_by(tenant_id=tenant_id, recommendation_id=recommendation.id)
                .order_by(OutcomeMeasurementPlan.created_at.desc())
                .first()
            )
        if plan is None:
            missing.append("measurement_plan")
            missing.append("outcome_observation")
            missing.append("realized_outcome_report")
        else:
            add("measurement_plan", plan.id, plan.content_hash, _iso(plan.created_at), "derived")

            observation = (
                self.session.query(OutcomeObservation)
                .filter_by(tenant_id=tenant_id, measurement_plan_id=plan.id)
                .order_by(OutcomeObservation.created_at.desc())
                .first()
            )
            if observation is None:
                missing.append("outcome_observation")
            else:
                reality = _OBSERVATION_SOURCE_TO_REALITY.get(observation.source, "derived")
                add("outcome_observation", observation.id, observation.content_hash, _iso(observation.created_at), reality)

            report = (
                self.session.query(RealizedOutcomeReport)
                .filter_by(tenant_id=tenant_id, measurement_plan_id=plan.id)
                .one_or_none()
            )
            if report is None:
                missing.append("realized_outcome_report")
            else:
                add("realized_outcome_report", report.id, report.content_hash, _iso(report.created_at), "derived")

        return references, sorted(set(missing)), unresolved_incident_ids, plan

    # -- lifecycle -----------------------------------------------------------

    def build(
        self, *, tenant_id: str, recommendation_id: str, created_by: str, measurement_plan_id: str | None = None,
    ) -> DecisionOutcomeEvidenceBundle:
        existing = (
            self.session.query(DecisionOutcomeEvidenceBundle)
            .filter_by(tenant_id=tenant_id, recommendation_id=recommendation_id)
            .filter(DecisionOutcomeEvidenceBundle.status != "sealed")
            .order_by(DecisionOutcomeEvidenceBundle.created_at.desc())
            .first()
        )

        references, missing, _unresolved, plan = self._gather(
            tenant_id=tenant_id, recommendation_id=recommendation_id, measurement_plan_id=measurement_plan_id
        )
        resolved_plan_id = plan.id if plan is not None else measurement_plan_id
        status = "incomplete" if missing else "complete"

        row = existing or DecisionOutcomeEvidenceBundle(
            id=f"decisionoutcomeevidence_{uuid4().hex}",
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            created_by=created_by,
        )
        row.measurement_plan_id = resolved_plan_id
        row.status = status
        row.manifest_json = json.dumps([ref.as_dict() for ref in references], sort_keys=True, separators=(",", ":"))
        row.missing_resources_json = json.dumps(missing, sort_keys=True, separators=(",", ":"))
        row.manifest_hash = manifest_hash(references)
        row.chain_hash = chain_hash(references)
        row.content_hash = compute_content_hash(
            references, recommendation_id=recommendation_id, measurement_plan_id=resolved_plan_id
        )
        row.updated_at = _utc_now()
        if existing is None:
            self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def seal(self, *, tenant_id: str, bundle_id: str, sealed_by: str) -> DecisionOutcomeEvidenceBundle:
        row = self._get(tenant_id=tenant_id, bundle_id=bundle_id)
        if row.status == "sealed":
            return row

        # Re-gather rather than trust the stored manifest -- referenced rows
        # or terminal states may have changed (or vanished) since the last
        # `build()` call.
        references, missing, unresolved_incident_ids, plan = self._gather(
            tenant_id=tenant_id, recommendation_id=row.recommendation_id, measurement_plan_id=row.measurement_plan_id
        )
        if missing:
            raise EvidenceSealValidationError(f"evidence_bundle_incomplete:{','.join(missing)}")
        if unresolved_incident_ids:
            raise EvidenceSealValidationError(
                f"evidence_bundle_has_unresolved_safety_incidents:{','.join(sorted(unresolved_incident_ids))}"
            )

        recommendation = self.session.query(GovernedRecommendation).filter_by(
            tenant_id=tenant_id, id=row.recommendation_id
        ).one()
        if recommendation.status not in {"approved", "converted"}:
            raise EvidenceSealValidationError(f"recommendation_not_in_sealable_status:{recommendation.status}")

        action_draft = (
            self.session.query(GovernedActionDraft)
            .filter_by(tenant_id=tenant_id, recommendation_id=row.recommendation_id)
            .order_by(GovernedActionDraft.created_at.desc())
            .first()
        )
        run = (
            self.session.query(ExecutionRun)
            .filter_by(tenant_id=tenant_id, id=action_draft.converted_run_id)
            .one_or_none()
            if action_draft is not None and action_draft.converted_run_id is not None
            else None
        )
        if run is None or run.status not in _RUN_TERMINAL_STATUSES:
            raise EvidenceSealValidationError("execution_run_not_terminal")

        # `plan` is already the row `_gather` resolved above (falls back to
        # the most recent plan for this recommendation when
        # `row.measurement_plan_id` is still unset) -- re-querying by
        # `row.measurement_plan_id` here would use a stale/None id.
        if plan is None or plan.status not in _PLAN_TERMINAL_STATUSES:
            raise EvidenceSealValidationError("measurement_plan_not_terminal")
        row.measurement_plan_id = plan.id

        # Sec 14.5: only one sealed bundle per (recommendation, measurement
        # version) pair -- a `building`/`incomplete`/`complete` bundle for
        # the same pair can coexist and get sealed later, but never two
        # sealed ones.
        existing_sealed = (
            self.session.query(DecisionOutcomeEvidenceBundle)
            .filter_by(
                tenant_id=tenant_id, recommendation_id=row.recommendation_id,
                measurement_plan_id=plan.id, status="sealed",
            )
            .filter(DecisionOutcomeEvidenceBundle.id != row.id)
            .one_or_none()
        )
        if existing_sealed is not None:
            raise EvidenceSealValidationError(f"evidence_bundle_already_sealed_for_recommendation:{existing_sealed.id}")

        manifest_payload = [ref.as_dict() for ref in references]
        if contains_secret_like_field(manifest_payload):
            raise EvidenceSealValidationError("evidence_bundle_contains_secret_like_field")

        for ref in references:
            if ref.tenant_id != tenant_id:
                raise EvidenceSealValidationError(f"tenant_mismatch:{ref.resource_type}:{ref.resource_id}")

        row.manifest_json = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":"))
        row.missing_resources_json = "[]"
        row.manifest_hash = manifest_hash(references)
        row.chain_hash = chain_hash(references)
        row.content_hash = compute_content_hash(
            references, recommendation_id=row.recommendation_id, measurement_plan_id=row.measurement_plan_id
        )
        row.status = "sealed"
        row.sealed_at = _utc_now()
        row.sealed_by = sealed_by
        row.updated_at = row.sealed_at
        self.session.commit()
        self.session.refresh(row)
        return row

    def verify(self, *, tenant_id: str, bundle_id: str) -> dict:
        row = self._get(tenant_id=tenant_id, bundle_id=bundle_id)
        stored_manifest = json.loads(row.manifest_json)
        references = [
            ResourceReference(
                resource_type=item["resource_type"], resource_id=item["resource_id"],
                content_hash=item["content_hash"], created_at=item["created_at"],
                tenant_id=item["tenant_id"], reality_label=item["reality_label"],
            )
            for item in stored_manifest
        ]
        recomputed_manifest_hash = manifest_hash(references)
        recomputed_chain_hash = chain_hash(references)
        recomputed_content_hash = compute_content_hash(
            references, recommendation_id=row.recommendation_id, measurement_plan_id=row.measurement_plan_id
        )
        stored_intact = (
            recomputed_manifest_hash == row.manifest_hash
            and recomputed_chain_hash == row.chain_hash
            and recomputed_content_hash == row.content_hash
        )

        live_mismatches: list[str] = []
        if row.status == "sealed":
            live_references, live_missing, _unresolved, _plan = self._gather(
                tenant_id=tenant_id, recommendation_id=row.recommendation_id, measurement_plan_id=row.measurement_plan_id
            )
            live_by_key = {(ref.resource_type, ref.resource_id): ref.content_hash for ref in live_references}
            for ref in references:
                live_hash = live_by_key.get((ref.resource_type, ref.resource_id))
                if live_hash is None or live_hash != ref.content_hash:
                    live_mismatches.append(f"{ref.resource_type}:{ref.resource_id}")
            live_mismatches.extend(f"missing_now:{item}" for item in live_missing)

        verified = stored_intact and not live_mismatches
        return {
            "bundle_id": row.id,
            "status": row.status,
            "verified": verified,
            "stored_hashes_intact": stored_intact,
            "live_mismatches": live_mismatches,
            "manifest_hash": row.manifest_hash,
            "content_hash": row.content_hash,
            "chain_hash": row.chain_hash,
        }

    def export(self, *, tenant_id: str, bundle_id: str) -> dict:
        row = self._get(tenant_id=tenant_id, bundle_id=bundle_id)
        payload = {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "recommendation_id": row.recommendation_id,
            "measurement_plan_id": row.measurement_plan_id,
            "status": row.status,
            "manifest": json.loads(row.manifest_json),
            "missing_resources": json.loads(row.missing_resources_json),
            "manifest_hash": row.manifest_hash,
            "content_hash": row.content_hash,
            "chain_hash": row.chain_hash,
            "created_by": row.created_by,
            "created_at": _iso(row.created_at),
            "sealed_at": _iso(row.sealed_at) if row.sealed_at else None,
            "sealed_by": row.sealed_by,
        }
        if contains_secret_like_field(payload):
            raise EvidenceIntegrityFailed("evidence_bundle_export_contains_secret_like_field")
        return payload
