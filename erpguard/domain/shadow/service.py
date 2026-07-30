"""Effects-free shadow evaluation, review and outcome reconciliation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from math import sqrt
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.db.model_packages.event_links import CanonicalEventObject
from erpguard.db.model_packages.events import CanonicalEvent
from erpguard.db.model_packages.proof import ProcessProof
from erpguard.db.model_packages.replay import ProcessReplay
from erpguard.db.model_packages.shadow import (
    ShadowCaseResult,
    ShadowCaseReview,
    ShadowDeployment,
    ShadowOutcomeObservation,
)
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.processes.registry import ProcessRegistry
from erpguard.domain.replays.engine import ReplayEngine
from erpguard.domain.shadow.types import (
    ReviewerLabel,
    ShadowDecision,
    ShadowEvaluationInput,
    ShadowOutcomeInput,
)
from erpguard.domain.variants.discovery import CaseTrace, TraceEvent


class ShadowValidationError(ValueError):
    pass


class ShadowNotFound(KeyError):
    pass


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _decision(result) -> ShadowDecision:
    return ShadowDecision(
        status=result.status,
        decision_trace=[item.model_dump(mode="json") for item in result.decision_trace],
        predicted_effects=[item.model_dump(mode="json") for item in result.predicted_effects],
        safety_violations=[item.model_dump(mode="json") for item in result.safety_violations],
        unsupported_decisions=result.unsupported_decisions,
        decision_coverage_rate=result.decision_coverage_rate,
    )


def _differences(active: ShadowDecision, candidate: ShadowDecision) -> list[str]:
    categories: set[str] = set()
    if active.status != candidate.status:
        categories.add("status_changed")
    active_traces = {item["decision_name"]: item for item in active.decision_trace}
    candidate_traces = {item["decision_name"]: item for item in candidate.decision_trace}
    if set(active_traces) - set(candidate_traces):
        categories.add("decision_removed")
    if set(candidate_traces) - set(active_traces):
        categories.add("decision_added")
    for name in set(active_traces) & set(candidate_traces):
        if active_traces[name].get("outcome") != candidate_traces[name].get("outcome"):
            categories.add("decision_outcome_changed")
        if active_traces[name].get("risk_level") != candidate_traces[name].get("risk_level"):
            categories.add("risk_changed")
    if active.safety_violations != candidate.safety_violations:
        categories.add("safety_violation_changed")
    if active.predicted_effects != candidate.predicted_effects:
        categories.add("predicted_effect_changed")
    if active.unsupported_decisions or candidate.unsupported_decisions:
        categories.add("incomplete_decision_coverage")
    return sorted(categories)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class ShadowService:
    def __init__(self, session: Session):
        self.session = session
        self.engine = ReplayEngine()

    def create_deployment(
        self,
        *,
        tenant_id: str,
        candidate_id: str,
        proof_id: str,
        object_type: str,
        agreement_threshold: float,
        minimum_case_count: int = 30,
        minimum_decision_coverage: float = 1.0,
        minimum_review_coverage: float = 0.5,
        minimum_outcome_reconciliation: float = 0.5,
        observation_window_hours: int = 168,
        created_by: str,
    ) -> ShadowDeployment:
        candidate = (
            self.session.query(ProcessCandidate)
            .filter_by(tenant_id=tenant_id, id=candidate_id)
            .one_or_none()
        )
        if candidate is None:
            raise ShadowNotFound("candidate_not_found")
        if candidate.status != "submitted" or candidate.validation_status != "valid":
            raise ShadowValidationError("shadow_requires_submitted_valid_candidate")
        proof = (
            self.session.query(ProcessProof)
            .filter_by(tenant_id=tenant_id, id=proof_id)
            .one_or_none()
        )
        if proof is None:
            raise ShadowNotFound("proof_not_found")
        if proof.recommendation != "eligible_for_shadow":
            raise ShadowValidationError("proof_not_eligible_for_shadow")
        baseline_replay = (
            self.session.query(ProcessReplay)
            .filter_by(tenant_id=tenant_id, id=proof.baseline_replay_id)
            .one_or_none()
        )
        candidate_replay = (
            self.session.query(ProcessReplay)
            .filter_by(tenant_id=tenant_id, id=proof.candidate_replay_id)
            .one_or_none()
        )
        if baseline_replay is None or candidate_replay is None:
            raise ShadowValidationError("proof_replay_not_found")
        if (
            baseline_replay.process_key != candidate.process_key
            or candidate_replay.process_key != candidate.process_key
            or baseline_replay.version != candidate.base_version
            or candidate_replay.version != candidate.candidate_version
            or baseline_replay.object_type != object_type
            or candidate_replay.object_type != object_type
        ):
            raise ShadowValidationError("proof_candidate_scope_mismatch")
        if baseline_replay.status != "frozen" or candidate_replay.status != "frozen":
            raise ShadowValidationError("shadow_requires_frozen_replays")
        active_row = ProcessRegistry(self.session).get(
            candidate.process_key,
            candidate.base_version,
        )
        if active_row is None:
            raise ShadowValidationError("active_process_definition_not_found")
        try:
            active_definition = ProcessDefinitionDocument.model_validate_json(
                active_row.definition_json
            )
            candidate_definition = ProcessDefinitionDocument.model_validate_json(
                candidate.candidate_definition_json
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise ShadowValidationError("candidate_definition_integrity_failed") from exc
        if (
            candidate_definition.process_key != candidate.process_key
            or candidate_definition.version != candidate.candidate_version
            or stable_digest(candidate_definition.model_dump(mode="json"))
            != candidate.candidate_definition_digest
            or stable_digest(active_definition.model_dump(mode="json"))
            != candidate.base_definition_digest
        ):
            raise ShadowValidationError("candidate_definition_integrity_failed")

        row = ShadowDeployment(
            id=f"shadow_{uuid4().hex}",
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            proof_id=proof.id,
            process_key=candidate.process_key,
            active_version=candidate.base_version,
            candidate_version=candidate.candidate_version,
            object_type=object_type,
            status="shadow",
            agreement_threshold=agreement_threshold,
            minimum_case_count=minimum_case_count,
            minimum_decision_coverage=minimum_decision_coverage,
            minimum_review_coverage=minimum_review_coverage,
            minimum_outcome_reconciliation=minimum_outcome_reconciliation,
            observation_window_hours=observation_window_hours,
            no_effects=True,
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_deployment(self, *, tenant_id: str, deployment_id: str) -> ShadowDeployment:
        row = (
            self.session.query(ShadowDeployment)
            .filter_by(tenant_id=tenant_id, id=deployment_id)
            .one_or_none()
        )
        if row is None:
            raise ShadowNotFound("shadow_deployment_not_found")
        return row

    def evaluate_case(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        evaluation: ShadowEvaluationInput,
    ) -> ShadowCaseResult:
        deployment = self.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)
        trace = CaseTrace(
            case_id=evaluation.case_id,
            object_type=deployment.object_type,
            variant_id=f"shadow_{stable_digest(evaluation.event_types)[:16]}",
            events=tuple(
                TraceEvent(
                    event_key=f"shadow-event-{index}",
                    event_type=event_type,
                    timestamp=f"2000-01-01T00:00:{index:02d}+00:00",
                )
                for index, event_type in enumerate(evaluation.event_types)
            ),
            duration_seconds=None,
        )
        return self.evaluate_trace(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            trace=trace,
            object_attributes=evaluation.object_attributes,
            idempotency_key=evaluation.idempotency_key,
            input_hash=stable_digest(evaluation.model_dump(mode="json")),
            evaluation_mode="manual_api",
            canonical_trace_hash=None,
            trace_provenance={
                "extraction_mode": "manual_api",
                "source": "synthetic",
                "event_count": len(trace.events),
            },
            actual_outcome=evaluation.actual_outcome,
        )

    def evaluate_trace(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        trace: CaseTrace,
        object_attributes: dict[str, Any],
        idempotency_key: str,
        input_hash: str,
        evaluation_mode: str,
        canonical_trace_hash: str | None,
        trace_provenance: dict[str, Any],
        actual_outcome: dict[str, Any] | None = None,
    ) -> ShadowCaseResult:
        deployment = self.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)
        existing = (
            self.session.query(ShadowCaseResult)
            .filter_by(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                idempotency_key=idempotency_key,
            )
            .one_or_none()
        )
        if existing is not None:
            if existing.input_hash != input_hash:
                raise ShadowValidationError("shadow_idempotency_conflict")
            return existing

        active_row = ProcessRegistry(self.session).get(
            deployment.process_key,
            deployment.active_version,
        )
        candidate = (
            self.session.query(ProcessCandidate)
            .filter_by(tenant_id=tenant_id, id=deployment.candidate_id)
            .one()
        )
        if active_row is None:
            raise ShadowValidationError("active_process_definition_not_found")
        active_definition = ProcessDefinitionDocument.model_validate_json(active_row.definition_json)
        candidate_definition = ProcessDefinitionDocument.model_validate_json(
            candidate.candidate_definition_json
        )
        active_result = self.engine.run_case(
            process_key=deployment.process_key,
            version=deployment.active_version,
            object_type=deployment.object_type,
            case_trace=trace,
            definition=active_definition,
            object_attributes=object_attributes,
        )
        candidate_result = self.engine.run_case(
            process_key=deployment.process_key,
            version=deployment.candidate_version,
            object_type=deployment.object_type,
            case_trace=trace,
            definition=candidate_definition,
            object_attributes=object_attributes,
        )
        active_decision = _decision(active_result)
        candidate_decision = _decision(candidate_result)
        differences = _differences(active_decision, candidate_decision)
        content = {
            "deployment_id": deployment.id,
            "case_id": trace.case_id,
            "input_hash": input_hash,
            "active_decision": active_decision.model_dump(mode="json"),
            "candidate_decision": candidate_decision.model_dump(mode="json"),
            "difference_categories": differences,
            "actual_outcome": actual_outcome,
            "evaluation_mode": evaluation_mode,
            "canonical_trace_hash": canonical_trace_hash,
            "trace_provenance": trace_provenance,
        }
        row = ShadowCaseResult(
            id=f"shadowcase_{uuid4().hex}",
            tenant_id=tenant_id,
            deployment_id=deployment.id,
            case_id=trace.case_id,
            idempotency_key=idempotency_key,
            input_hash=input_hash,
            active_decision_json=_dump(active_decision.model_dump(mode="json")),
            candidate_decision_json=_dump(candidate_decision.model_dump(mode="json")),
            agreement=not differences,
            difference_categories_json=_dump(differences),
            actual_outcome_json=_dump(actual_outcome) if actual_outcome is not None else None,
            evaluation_mode=evaluation_mode,
            canonical_trace_hash=canonical_trace_hash,
            trace_provenance_json=_dump(trace_provenance),
            variant_id=trace.variant_id,
            event_count=len(trace.events),
            first_event_at=trace.events[0].timestamp if trace.events else None,
            last_event_at=trace.events[-1].timestamp if trace.events else None,
            deterministic_hash=stable_digest(content),
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_cases(self, *, tenant_id: str, deployment_id: str) -> list[ShadowCaseResult]:
        self.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)
        return (
            self.session.query(ShadowCaseResult)
            .filter_by(tenant_id=tenant_id, deployment_id=deployment_id)
            .order_by(ShadowCaseResult.evaluated_at.asc(), ShadowCaseResult.id.asc())
            .all()
        )

    def get_case(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        case_result_id: str,
    ) -> ShadowCaseResult:
        row = (
            self.session.query(ShadowCaseResult)
            .filter_by(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                id=case_result_id,
            )
            .one_or_none()
        )
        if row is None:
            raise ShadowNotFound("shadow_case_not_found")
        return row

    def add_review(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        case_result_id: str,
        reviewer_id: str,
        label: ReviewerLabel,
        notes: str,
    ) -> ShadowCaseReview:
        self.get_case(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
        )
        row = ShadowCaseReview(
            id=f"shadowreview_{uuid4().hex}",
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            shadow_case_result_id=case_result_id,
            reviewer_id=reviewer_id,
            label=label,
            notes=notes,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def reviews_for_case(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        case_result_id: str,
    ) -> list[ShadowCaseReview]:
        self.get_case(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
        )
        return (
            self.session.query(ShadowCaseReview)
            .filter_by(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                shadow_case_result_id=case_result_id,
            )
            .order_by(ShadowCaseReview.created_at.asc(), ShadowCaseReview.id.asc())
            .all()
        )

    def add_outcome(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        case_result_id: str,
        recorded_by: str,
        outcome: ShadowOutcomeInput,
    ) -> ShadowOutcomeObservation:
        case_result = self.get_case(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
        )
        content = outcome.model_dump(mode="json")
        content_hash = stable_digest(content)
        existing = (
            self.session.query(ShadowOutcomeObservation)
            .filter_by(
                tenant_id=tenant_id,
                shadow_case_result_id=case_result_id,
                idempotency_key=outcome.idempotency_key,
            )
            .one_or_none()
        )
        if existing is not None:
            if existing.deterministic_hash != content_hash:
                raise ShadowValidationError("shadow_outcome_idempotency_conflict")
            return existing
        if outcome.source_event_ids:
            provenance = json.loads(case_result.trace_provenance_json)
            canonical_object_id = provenance.get("object_id")
            if not canonical_object_id:
                raise ShadowValidationError("outcome_source_requires_canonical_case")
            found = (
                self.session.query(CanonicalEvent.id)
                .join(
                    CanonicalEventObject,
                    CanonicalEventObject.event_id == CanonicalEvent.id,
                )
                .filter(
                    CanonicalEvent.tenant_id == tenant_id,
                    CanonicalEvent.id.in_(set(outcome.source_event_ids)),
                    CanonicalEventObject.tenant_id == tenant_id,
                    CanonicalEventObject.object_id == canonical_object_id,
                )
                .distinct()
                .all()
            )
            if len(found) != len(set(outcome.source_event_ids)):
                raise ShadowValidationError("outcome_source_event_not_found")
        row = ShadowOutcomeObservation(
            id=f"shadowoutcome_{uuid4().hex}",
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            shadow_case_result_id=case_result_id,
            idempotency_key=outcome.idempotency_key,
            outcome_json=_dump(outcome.outcome),
            observed_decision_status=outcome.observed_decision_status,
            provenance=outcome.provenance,
            source_event_ids_json=_dump(outcome.source_event_ids),
            observed_at=outcome.observed_at,
            recorded_by=recorded_by,
            deterministic_hash=content_hash,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def outcomes_for_case(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        case_result_id: str,
    ) -> list[ShadowOutcomeObservation]:
        self.get_case(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
        )
        return (
            self.session.query(ShadowOutcomeObservation)
            .filter_by(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                shadow_case_result_id=case_result_id,
            )
            .order_by(
                ShadowOutcomeObservation.observed_at.asc(),
                ShadowOutcomeObservation.created_at.asc(),
                ShadowOutcomeObservation.id.asc(),
            )
            .all()
        )

    @staticmethod
    def _wilson(successes: int, total: int) -> dict[str, float] | None:
        if not total:
            return None
        z = 1.959963984540054
        proportion = successes / total
        denominator = 1 + z * z / total
        centre = (proportion + z * z / (2 * total)) / denominator
        margin = (
            z
            * sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
            / denominator
        )
        return {
            "lower": max(0.0, centre - margin),
            "upper": min(1.0, centre + margin),
        }

    def dashboard(
        self,
        *,
        tenant_id: str,
        deployment_id: str,
        canonical_case_count: int | None = None,
    ) -> dict[str, Any]:
        deployment = self.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)
        all_cases = self.list_cases(tenant_id=tenant_id, deployment_id=deployment_id)
        latest_by_case = {row.case_id: row for row in all_cases}
        cases = list(latest_by_case.values())
        operational_cases = [
            row for row in cases if row.evaluation_mode == "canonical_feed"
        ]
        result_case_ids = {row.id: row.case_id for row in cases}
        operational_result_ids = {row.id: row.case_id for row in operational_cases}
        agreements = sum(1 for row in cases if row.agreement)
        categories = Counter(
            category
            for row in cases
            for category in json.loads(row.difference_categories_json)
        )
        reviews = (
            self.session.query(ShadowCaseReview)
            .filter_by(tenant_id=tenant_id, deployment_id=deployment_id)
            .order_by(ShadowCaseReview.created_at.asc(), ShadowCaseReview.id.asc())
            .all()
        )
        latest_review_by_case: dict[str, ShadowCaseReview] = {}
        for review in reviews:
            case_id = result_case_ids.get(review.shadow_case_result_id)
            if case_id is not None:
                latest_review_by_case[case_id] = review
        labels = Counter(row.label for row in latest_review_by_case.values())
        operational_reviews = {
            operational_result_ids[review.shadow_case_result_id]: review
            for review in reviews
            if review.shadow_case_result_id in operational_result_ids
        }
        operational_labels = Counter(row.label for row in operational_reviews.values())
        outcomes = (
            self.session.query(ShadowOutcomeObservation)
            .filter_by(tenant_id=tenant_id, deployment_id=deployment_id)
            .order_by(
                ShadowOutcomeObservation.observed_at.asc(),
                ShadowOutcomeObservation.created_at.asc(),
                ShadowOutcomeObservation.id.asc(),
            )
            .all()
        )
        latest_outcome_by_case: dict[str, ShadowOutcomeObservation] = {}
        for outcome in outcomes:
            case_id = result_case_ids.get(outcome.shadow_case_result_id)
            if case_id is not None:
                latest_outcome_by_case[case_id] = outcome
        evaluated_count = len(cases)
        operational_count = len(operational_cases)
        rate = agreements / evaluated_count if evaluated_count else None
        operational_agreements = sum(1 for row in operational_cases if row.agreement)
        operational_rate = (
            operational_agreements / operational_count if operational_count else None
        )
        review_coverage = (
            len(operational_reviews) / operational_count if operational_count else 0.0
        )
        operational_outcomes = {
            case_id: outcome
            for case_id, outcome in latest_outcome_by_case.items()
            if case_id in {row.case_id for row in operational_cases}
        }
        outcome_coverage = (
            len(operational_outcomes) / operational_count if operational_count else 0.0
        )
        decision_coverage = (
            min(
                min(
                    json.loads(row.active_decision_json)["decision_coverage_rate"],
                    json.loads(row.candidate_decision_json)["decision_coverage_rate"],
                )
                for row in operational_cases
            )
            if operational_cases
            else 0.0
        )
        comparable_outcomes = [
            (row, operational_outcomes[row.case_id])
            for row in operational_cases
            if row.case_id in operational_outcomes
            and operational_outcomes[row.case_id].observed_decision_status is not None
        ]
        accurate_outcomes = sum(
            1
            for row, outcome in comparable_outcomes
            if json.loads(row.candidate_decision_json)["status"]
            == outcome.observed_decision_status
        )
        outcome_accuracy = (
            accurate_outcomes / len(comparable_outcomes) if comparable_outcomes else None
        )
        unsafe_count = operational_labels["unsafe_candidate"]
        elapsed_hours = (
            datetime.now(timezone.utc) - _aware(deployment.created_at)
        ).total_seconds() / 3600
        window_completed = elapsed_hours >= deployment.observation_window_hours
        canary_checks = {
            "minimum_case_count": operational_count >= deployment.minimum_case_count,
            "agreement_threshold": (
                operational_rate is not None
                and operational_rate >= deployment.agreement_threshold
            ),
            "decision_coverage": decision_coverage >= deployment.minimum_decision_coverage,
            "no_unresolved_unsafe_candidate": unsafe_count == 0,
            "review_coverage": review_coverage >= deployment.minimum_review_coverage,
            "outcome_reconciliation": (
                outcome_coverage >= deployment.minimum_outcome_reconciliation
            ),
            "observation_window_completed": window_completed,
        }
        eligible = all(canary_checks.values())
        variant_counts = Counter(
            row.variant_id or "unknown" for row in operational_cases
        )
        return {
            "deployment_id": deployment.id,
            "status": deployment.status,
            "no_effects": deployment.no_effects,
            "evaluated_case_count": evaluated_count,
            "operational_case_count": operational_count,
            "agreement_count": agreements,
            "disagreement_count": evaluated_count - agreements,
            "agreement_rate": rate,
            "agreement_threshold": deployment.agreement_threshold,
            "threshold_met": rate >= deployment.agreement_threshold if rate is not None else False,
            "difference_category_counts": dict(sorted(categories.items())),
            "review_label_counts": dict(sorted(labels.items())),
            "review_count": len(latest_review_by_case),
            "canonical_case_count": canonical_case_count,
            "case_coverage_rate": (
                min(1.0, operational_count / canonical_case_count)
                if canonical_case_count
                else None
            ),
            "decision_coverage_rate": decision_coverage,
            "review_coverage_rate": review_coverage,
            "outcome_reconciliation_rate": outcome_coverage,
            "candidate_preferred_rate": (
                operational_labels["candidate_preferred"] / operational_count
                if operational_count
                else 0.0
            ),
            "unsafe_candidate_rate": (
                unsafe_count / operational_count if operational_count else 0.0
            ),
            "insufficient_evidence_rate": (
                operational_labels["insufficient_evidence"] / operational_count
                if operational_count
                else 0.0
            ),
            "outcome_accuracy": outcome_accuracy,
            "variant_distribution": dict(sorted(variant_counts.items())),
            "agreement_confidence_interval_95": self._wilson(
                operational_agreements,
                operational_count,
            ),
            "outcome_accuracy_confidence_interval_95": self._wilson(
                accurate_outcomes,
                len(comparable_outcomes),
            ),
            "observation_window_completed": window_completed,
            "canary_eligibility_checks": canary_checks,
            "recommendation": "eligible_for_canary" if eligible else "continue_shadow",
            "recommendation_is_advisory": True,
        }
