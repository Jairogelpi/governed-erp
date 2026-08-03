"""Spec 92 Workstream C: `OutcomeService` -- measurement plan lifecycle,
observation capture, evaluation. Approval reuses `ApprovalService`/
`Approval` exactly like Workstreams A/B.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.decision_intelligence import AnalyticalSnapshot, MarginAnalysis
from erpguard.db.model_packages.execution import Approval
from erpguard.db.model_packages.outcomes import (
    OutcomeMeasurementPlan,
    OutcomeObservation,
    RealizedOutcomeReport,
)
from erpguard.db.model_packages.recommendations import GovernedRecommendation
from erpguard.domain.outcomes.measurement import measure
from erpguard.domain.outcomes.types import ObservedMetrics
from erpguard.domain.processes.candidate_integrity import stable_digest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class OutcomePlanNotFound(KeyError):
    pass


class OutcomeReportNotFound(KeyError):
    pass


class OutcomeValidationError(ValueError):
    pass


class OutcomeApprovalRejected(OutcomeValidationError):
    pass


class OutcomeTransitionError(OutcomeValidationError):
    pass


_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"approved"},
    "approved": {"observing"},
    "observing": {"ready", "evaluated", "blocked", "inconclusive"},
    "ready": {"evaluated", "blocked", "inconclusive"},
    "evaluated": set(),
    "blocked": set(),
    "inconclusive": set(),
}


class OutcomeService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, plan_id: str) -> OutcomeMeasurementPlan:
        row = self.session.query(OutcomeMeasurementPlan).filter_by(tenant_id=tenant_id, id=plan_id).one_or_none()
        if row is None:
            raise OutcomePlanNotFound(plan_id)
        return row

    def get(self, *, tenant_id: str, plan_id: str) -> OutcomeMeasurementPlan:
        return self._get(tenant_id=tenant_id, plan_id=plan_id)

    def get_report(self, *, tenant_id: str, report_id: str) -> RealizedOutcomeReport:
        row = self.session.query(RealizedOutcomeReport).filter_by(tenant_id=tenant_id, id=report_id).one_or_none()
        if row is None:
            raise OutcomeReportNotFound(report_id)
        return row

    @staticmethod
    def approval_scope(plan: OutcomeMeasurementPlan) -> str:
        return f"outcome_measurement_plan:{plan.id}:approve:{plan.content_hash}"

    def _require_transition(self, *, current: str, target: str) -> None:
        if target not in _TRANSITIONS.get(current, set()):
            raise OutcomeTransitionError(f"cannot_transition_from:{current}:to:{target}")

    def create_plan(
        self,
        *,
        tenant_id: str,
        recommendation_id: str,
        execution_run_ids: list[str],
        comparison_method: str,
        observation_start: str,
        observation_end: str,
        created_by: str,
        minimum_data_coverage: float = 0.8,
        target_metrics: list[str] | None = None,
        assumptions: list[str] | None = None,
        implementation_cost: Decimal | None = None,
    ) -> OutcomeMeasurementPlan:
        recommendation = (
            self.session.query(GovernedRecommendation)
            .filter_by(tenant_id=tenant_id, id=recommendation_id)
            .one_or_none()
        )
        if recommendation is None:
            raise OutcomeValidationError("recommendation_not_found")
        if recommendation.status != "converted":
            raise OutcomeValidationError(f"recommendation_not_converted:{recommendation.status}")

        baseline_analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=recommendation.margin_analysis_id)
            .one_or_none()
        )
        if baseline_analysis is None or baseline_analysis.status == "blocked":
            raise OutcomeValidationError("baseline_margin_analysis_blocked_or_missing")

        from erpguard.db.model_packages.recommendations import GovernedActionDraft

        action_draft = (
            self.session.query(GovernedActionDraft)
            .filter_by(tenant_id=tenant_id, recommendation_id=recommendation_id, status="converted")
            .order_by(GovernedActionDraft.created_at.desc())
            .first()
        )
        if action_draft is None:
            raise OutcomeValidationError("no_converted_action_draft_for_recommendation")

        if implementation_cost is not None and implementation_cost < 0:
            raise OutcomeValidationError("implementation_cost_must_be_non_negative")

        content = {
            "recommendation_id": recommendation_id,
            "recommendation_content_hash": recommendation.content_hash,
            "action_draft_id": action_draft.id,
            "comparison_method": comparison_method,
            "observation_start": observation_start,
            "observation_end": observation_end,
            "implementation_cost": str(implementation_cost) if implementation_cost is not None else None,
        }
        row = OutcomeMeasurementPlan(
            id=f"outcomeplan_{uuid4().hex}",
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            margin_opportunity_id=recommendation.margin_opportunity_id,
            baseline_snapshot_id=recommendation.snapshot_id,
            baseline_analysis_id=recommendation.margin_analysis_id,
            action_draft_id=action_draft.id,
            execution_run_ids_json=_dump(execution_run_ids),
            metric_definition_version=baseline_analysis.metric_definition_version,
            target_metrics_json=_dump(target_metrics or ["net_revenue", "gross_margin", "gross_margin_percent"]),
            population_scope_json=recommendation.affected_population_json,
            comparison_method=comparison_method,
            observation_start=observation_start,
            observation_end=observation_end,
            minimum_data_coverage=minimum_data_coverage,
            implementation_cost=str(implementation_cost) if implementation_cost is not None else None,
            assumptions_json=_dump(assumptions or []),
            status="draft",
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def approve_plan(self, *, tenant_id: str, plan_id: str, approval_id: str, approver_actor_id: str) -> OutcomeMeasurementPlan:
        row = self._get(tenant_id=tenant_id, plan_id=plan_id)
        self._require_transition(current=row.status, target="approved")

        approval = self.session.query(Approval).filter_by(tenant_id=tenant_id, id=approval_id).one_or_none()
        if approval is None:
            raise OutcomeApprovalRejected("approval_not_found")
        if approval.used_at is not None:
            raise OutcomeApprovalRejected("approval_already_used")
        if approval.actor_id == row.created_by:
            raise OutcomeApprovalRejected("plan_creator_cannot_approve")
        if approval.actor_id != approver_actor_id:
            raise OutcomeApprovalRejected("approval_actor_mismatch")
        if approval.scope != self.approval_scope(row):
            raise OutcomeApprovalRejected("approval_scope_mismatch")

        approval.used_at = _utc_now()
        approval.used_by_run_id = row.id
        row.status = "approved"
        self.session.commit()
        self.session.refresh(row)
        return row

    def start(self, *, tenant_id: str, plan_id: str) -> OutcomeMeasurementPlan:
        row = self._get(tenant_id=tenant_id, plan_id=plan_id)
        self._require_transition(current=row.status, target="observing")
        row.status = "observing"
        row.started_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def capture_followup_fixture(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        observed: ObservedMetrics,
        created_by: str,
        source: str = "fixture",
        observed_at: datetime | None = None,
    ) -> OutcomeObservation:
        if source not in {"fixture", "manual_import"}:
            raise OutcomeValidationError(f"invalid_fixture_source:{source}")
        row = self._get(tenant_id=tenant_id, plan_id=plan_id)
        if row.status not in {"observing"}:
            raise OutcomeTransitionError(f"plan_not_observing:{row.status}")

        metrics_payload = observed.model_dump(mode="json")
        observation = OutcomeObservation(
            id=f"outcomeobs_{uuid4().hex}",
            tenant_id=tenant_id,
            measurement_plan_id=plan_id,
            followup_snapshot_id=None,
            followup_analysis_id=None,
            source=source,
            observed_at=observed_at or _utc_now(),
            metrics_json=_dump(metrics_payload),
            quality_json=_dump({"cost_coverage_rate": observed.cost_coverage_rate}),
            content_hash=stable_digest(metrics_payload),
            created_by=created_by,
        )
        self.session.add(observation)
        row.status = "ready"
        row.ready_at = _utc_now()
        self.session.commit()
        self.session.refresh(observation)
        return observation

    def capture_followup_live(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        followup_snapshot_id: str,
        followup_analysis_id: str,
        created_by: str,
    ) -> OutcomeObservation:
        row = self._get(tenant_id=tenant_id, plan_id=plan_id)
        if row.status not in {"observing"}:
            raise OutcomeTransitionError(f"plan_not_observing:{row.status}")

        snapshot = (
            self.session.query(AnalyticalSnapshot)
            .filter_by(tenant_id=tenant_id, id=followup_snapshot_id)
            .one_or_none()
        )
        analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=followup_analysis_id)
            .one_or_none()
        )
        if snapshot is None or analysis is None:
            raise OutcomeValidationError("followup_snapshot_or_analysis_not_found")

        current = json.loads(analysis.current_metrics_json)
        values = current.get("values", {})
        observed = ObservedMetrics(
            net_revenue=_metric_value(values, "net_revenue"),
            gross_margin=_metric_value(values, "gross_margin"),
            gross_margin_percent=_metric_value(values, "gross_margin_percent"),
            currency=snapshot.currency,
            metric_definition_version=analysis.metric_definition_version,
            cost_coverage_rate=1.0 if analysis.status != "blocked" else 0.0,
        )
        metrics_payload = observed.model_dump(mode="json")
        observation = OutcomeObservation(
            id=f"outcomeobs_{uuid4().hex}",
            tenant_id=tenant_id,
            measurement_plan_id=plan_id,
            followup_snapshot_id=followup_snapshot_id,
            followup_analysis_id=followup_analysis_id,
            source="live_odoo_read",
            observed_at=_utc_now(),
            metrics_json=_dump(metrics_payload),
            quality_json=_dump({}),
            content_hash=stable_digest(metrics_payload),
            created_by=created_by,
        )
        self.session.add(observation)
        row.status = "ready"
        row.ready_at = _utc_now()
        self.session.commit()
        self.session.refresh(observation)
        return observation

    def evaluate(self, *, tenant_id: str, plan_id: str, created_by: str) -> RealizedOutcomeReport:
        row = self._get(tenant_id=tenant_id, plan_id=plan_id)
        if row.status != "ready":
            raise OutcomeTransitionError(f"plan_not_ready:{row.status}")

        observation = (
            self.session.query(OutcomeObservation)
            .filter_by(tenant_id=tenant_id, measurement_plan_id=plan_id)
            .order_by(OutcomeObservation.created_at.desc())
            .first()
        )
        if observation is None:
            raise OutcomeValidationError("no_observation_to_evaluate")

        recommendation = (
            self.session.query(GovernedRecommendation)
            .filter_by(tenant_id=tenant_id, id=row.recommendation_id)
            .one()
        )
        baseline_analysis = (
            self.session.query(MarginAnalysis)
            .filter_by(tenant_id=tenant_id, id=row.baseline_analysis_id)
            .one()
        )
        baseline_snapshot = (
            self.session.query(AnalyticalSnapshot)
            .filter_by(tenant_id=tenant_id, id=row.baseline_snapshot_id)
            .one()
        )
        baseline_period_metrics = json.loads(baseline_analysis.current_metrics_json)
        observed_payload = json.loads(observation.metrics_json)
        observed = ObservedMetrics.model_validate(observed_payload)

        result = measure(
            comparison_method=row.comparison_method,
            baseline_period_metrics=baseline_period_metrics,
            baseline_metric_definition_version=baseline_analysis.metric_definition_version,
            baseline_currency=baseline_snapshot.currency,
            observed=observed,
            minimum_data_coverage=row.minimum_data_coverage,
            estimated_base=Decimal(recommendation.estimated_impact_base),
            implementation_cost=Decimal(row.implementation_cost) if row.implementation_cost is not None else None,
        )

        content = {
            "plan_content_hash": row.content_hash,
            "observation_content_hash": observation.content_hash,
            "result": {k: str(v) if isinstance(v, Decimal) else v for k, v in result.items()},
        }
        report = RealizedOutcomeReport(
            id=f"outcomereport_{uuid4().hex}",
            tenant_id=tenant_id,
            measurement_plan_id=plan_id,
            recommendation_id=row.recommendation_id,
            opportunity_id=row.margin_opportunity_id,
            estimated_conservative=recommendation.estimated_impact_conservative,
            estimated_base=recommendation.estimated_impact_base,
            estimated_optimistic=recommendation.estimated_impact_optimistic,
            observed_revenue_change=_str_or_none(result["observed_revenue_change"]),
            observed_margin_change=_str_or_none(result["observed_margin_change"]),
            observed_margin_percent_change=_str_or_none(result["observed_margin_percent_change"]),
            observed_refund_change=None,
            realized_value=_str_or_none(result["realized_value"]),
            implementation_cost=row.implementation_cost,
            net_realized_value=_str_or_none(result["net_realized_value"]),
            variance_from_base_estimate=_str_or_none(result["variance_from_base_estimate"]),
            result_classification=result["result_classification"],
            confidence_band=recommendation.confidence_band,
            limitations_json=_dump(result["limitations"]),
            assumptions_json=row.assumptions_json,
            metric_definition_version=row.metric_definition_version,
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(report)
        row.status = result["result_classification"] if result["result_classification"] in {"blocked", "inconclusive"} else "evaluated"
        row.evaluated_at = _utc_now()
        self.session.commit()
        self.session.refresh(report)
        return report


def _metric_value(values: dict, key: str) -> Decimal | None:
    entry = values.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return Decimal(str(value)) if value is not None else None


def _str_or_none(value) -> str | None:
    return str(value) if value is not None else None
