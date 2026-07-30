"""Phase 18 shadow service.

This module deliberately imports no connector, execution-permit or ERP
transport code. It evaluates two immutable process definitions in memory and
stores append-only comparison evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.db.model_packages.proof import ProcessProof
from erpguard.db.model_packages.replay import ProcessReplay
from erpguard.db.model_packages.shadow import ShadowCaseResult, ShadowCaseReview, ShadowDeployment
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.processes.registry import ProcessRegistry
from erpguard.domain.replays.engine import ReplayEngine
from erpguard.domain.shadow.types import ReviewerLabel, ShadowDecision, ShadowEvaluationInput
from erpguard.domain.variants.discovery import CaseTrace, TraceEvent


class ShadowValidationError(ValueError):
    pass


class ShadowNotFound(KeyError):
    pass


def _dump(value) -> str:
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
        input_hash = stable_digest(evaluation.model_dump(mode="json"))
        existing = (
            self.session.query(ShadowCaseResult)
            .filter_by(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                idempotency_key=evaluation.idempotency_key,
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
        active_result = self.engine.run_case(
            process_key=deployment.process_key,
            version=deployment.active_version,
            object_type=deployment.object_type,
            case_trace=trace,
            definition=active_definition,
            object_attributes=evaluation.object_attributes,
        )
        candidate_result = self.engine.run_case(
            process_key=deployment.process_key,
            version=deployment.candidate_version,
            object_type=deployment.object_type,
            case_trace=trace,
            definition=candidate_definition,
            object_attributes=evaluation.object_attributes,
        )
        active_decision = _decision(active_result)
        candidate_decision = _decision(candidate_result)
        differences = _differences(active_decision, candidate_decision)
        content = {
            "deployment_id": deployment.id,
            "case_id": evaluation.case_id,
            "input_hash": input_hash,
            "active_decision": active_decision.model_dump(mode="json"),
            "candidate_decision": candidate_decision.model_dump(mode="json"),
            "difference_categories": differences,
            "actual_outcome": evaluation.actual_outcome,
        }
        row = ShadowCaseResult(
            id=f"shadowcase_{uuid4().hex}",
            tenant_id=tenant_id,
            deployment_id=deployment.id,
            case_id=evaluation.case_id,
            idempotency_key=evaluation.idempotency_key,
            input_hash=input_hash,
            active_decision_json=_dump(active_decision.model_dump(mode="json")),
            candidate_decision_json=_dump(candidate_decision.model_dump(mode="json")),
            agreement=not differences,
            difference_categories_json=_dump(differences),
            actual_outcome_json=_dump(evaluation.actual_outcome) if evaluation.actual_outcome is not None else None,
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

    def dashboard(self, *, tenant_id: str, deployment_id: str) -> dict:
        deployment = self.get_deployment(tenant_id=tenant_id, deployment_id=deployment_id)
        cases = self.list_cases(tenant_id=tenant_id, deployment_id=deployment_id)
        agreements = sum(1 for row in cases if row.agreement)
        categories = Counter(
            category
            for row in cases
            for category in json.loads(row.difference_categories_json)
        )
        reviews = (
            self.session.query(ShadowCaseReview)
            .filter_by(tenant_id=tenant_id, deployment_id=deployment_id)
            .all()
        )
        labels = Counter(row.label for row in reviews)
        rate = agreements / len(cases) if cases else None
        return {
            "deployment_id": deployment.id,
            "status": deployment.status,
            "no_effects": deployment.no_effects,
            "evaluated_case_count": len(cases),
            "agreement_count": agreements,
            "disagreement_count": len(cases) - agreements,
            "agreement_rate": rate,
            "agreement_threshold": deployment.agreement_threshold,
            "threshold_met": rate >= deployment.agreement_threshold if rate is not None else False,
            "difference_category_counts": dict(sorted(categories.items())),
            "review_label_counts": dict(sorted(labels.items())),
            "review_count": len(reviews),
        }
