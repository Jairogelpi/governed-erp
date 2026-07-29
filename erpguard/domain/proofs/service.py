"""Proof of Improvement service (master spec section 17 / Phase 13)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.proof import ProcessProof
from erpguard.db.model_packages.replay import ProcessReplay, ProcessReplayCase
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.proofs.eligibility import determine_recommendation
from erpguard.domain.proofs.metrics import compute_metric_comparisons
from erpguard.domain.proofs.regression_classifier import classify_regressions
from erpguard.domain.proofs.types import ProofOfImprovement, ReproducibilitySummary, SafetySummary


class ProofValidationError(ValueError):
    pass


class ProofNotFound(KeyError):
    pass


class ReplayNotFoundForProof(KeyError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_replay(session: Session, *, tenant_id: str, replay_id: str) -> ProcessReplay:
    row = session.query(ProcessReplay).filter_by(tenant_id=tenant_id, id=replay_id).one_or_none()
    if row is None:
        raise ReplayNotFoundForProof(replay_id)
    return row


def _load_cases(session: Session, *, tenant_id: str, replay_id: str) -> dict[str, ProcessReplayCase]:
    rows = (
        session.query(ProcessReplayCase)
        .filter_by(tenant_id=tenant_id, replay_id=replay_id)
        .order_by(ProcessReplayCase.case_id.asc())
        .all()
    )
    return {row.case_id: row for row in rows}


class ProofService:
    def __init__(self, session: Session):
        self.session = session

    def generate_proof(
        self,
        *,
        tenant_id: str,
        baseline_replay_id: str,
        candidate_replay_id: str,
        benchmark_version: str,
    ) -> ProcessProof:
        baseline = _load_replay(self.session, tenant_id=tenant_id, replay_id=baseline_replay_id)
        candidate = _load_replay(self.session, tenant_id=tenant_id, replay_id=candidate_replay_id)

        if baseline.status not in ("completed", "frozen"):
            raise ProofValidationError("baseline_replay_not_completed")
        if candidate.status not in ("completed", "frozen"):
            raise ProofValidationError("candidate_replay_not_completed")

        baseline_cases = _load_cases(self.session, tenant_id=tenant_id, replay_id=baseline.id)
        candidate_cases = _load_cases(self.session, tenant_id=tenant_id, replay_id=candidate.id)

        matched_case_ids = sorted(set(baseline_cases) & set(candidate_cases))
        if not matched_case_ids:
            raise ProofValidationError("no_overlapping_cases_between_replays")

        case_pairs = []
        for case_id in matched_case_ids:
            b = baseline_cases[case_id]
            c = candidate_cases[case_id]
            case_pairs.append(
                {
                    "case_id": case_id,
                    "baseline_status": b.status,
                    "baseline_decision_trace": json.loads(b.decision_trace_json),
                    "baseline_safety_violations": json.loads(b.safety_violations_json),
                    "candidate_status": c.status,
                    "candidate_decision_trace": json.loads(c.decision_trace_json),
                    "candidate_safety_violations": json.loads(c.safety_violations_json),
                }
            )

        regression_summaries, case_details = classify_regressions(case_pairs)
        critical_count = sum(item.count for item in regression_summaries if item.severity == "critical")

        candidate_statuses = [candidate_cases[cid].status for cid in matched_case_ids]
        baseline_statuses = [baseline_cases[cid].status for cid in matched_case_ids]
        metric_comparisons = compute_metric_comparisons(
            baseline_statuses=baseline_statuses,
            candidate_statuses=candidate_statuses,
            case_details=case_details,
        )

        evidence_completeness = sum(1 for s in candidate_statuses if s != "needs_clarification") / len(
            candidate_statuses
        )

        # "Deterministic": both replays are past `running` (completed/frozen,
        # already enforced above) and every matched case actually has a
        # persisted `deterministic_trace_hash` (i.e. the replay engine ran to
        # completion for it rather than leaving a gap) -- see
        # ReproducibilitySummary's docstring for what this does and doesn't
        # verify; it does not re-execute the policy engine.
        reproducible = all(
            baseline_cases[cid].deterministic_trace_hash and candidate_cases[cid].deterministic_trace_hash
            for cid in matched_case_ids
        )
        reproducibility_summary = ReproducibilitySummary(
            baseline_frozen=baseline.status == "frozen",
            candidate_frozen=candidate.status == "frozen",
            deterministic=reproducible,
        )

        recommendation, recommendation_basis, limitations = determine_recommendation(
            critical_regression_count=critical_count,
            evidence_completeness=evidence_completeness,
            reproducible=reproducible,
        )

        safety_summary = SafetySummary(
            critical_regressions=critical_count,
            forbidden_effects=sum(1 for s in candidate_statuses if s == "failed"),
        )

        dataset_version = f"{candidate.process_key}:{candidate.object_type}"
        baseline_process_version_id = f"{baseline.process_key}:{baseline.version}"
        candidate_process_version_id = f"{candidate.process_key}:{candidate.version}"
        generated_at = _utc_now()

        content_for_hash = {
            "baseline_replay_id": baseline.id,
            "candidate_replay_id": candidate.id,
            "dataset_version": dataset_version,
            "benchmark_version": benchmark_version,
            "metric_comparisons": [m.model_dump(mode="json") for m in metric_comparisons],
            "regressions": [r.model_dump(mode="json") for r in regression_summaries],
            "safety_summary": safety_summary.model_dump(mode="json"),
            "reproducibility_summary": reproducibility_summary.model_dump(mode="json"),
            "recommendation": recommendation,
            "recommendation_basis": recommendation_basis,
        }
        content_hash = stable_digest(content_for_hash)

        proof = ProofOfImprovement(
            proof_id=f"proof_{uuid4().hex}",
            baseline_process_version_id=baseline_process_version_id,
            candidate_process_version_id=candidate_process_version_id,
            replay_run_id=candidate.id,
            dataset_version=dataset_version,
            benchmark_version=benchmark_version,
            metric_comparisons=metric_comparisons,
            regressions=regression_summaries,
            safety_summary=safety_summary,
            reproducibility_summary=reproducibility_summary,
            evidence_refs=[baseline.id, candidate.id],
            recommendation=recommendation,
            recommendation_basis=recommendation_basis,
            limitations=limitations,
            generated_at=generated_at,
            content_hash=content_hash,
        )

        row = ProcessProof(
            id=proof.proof_id,
            tenant_id=tenant_id,
            baseline_replay_id=baseline.id,
            candidate_replay_id=candidate.id,
            dataset_version=dataset_version,
            benchmark_version=benchmark_version,
            metric_comparisons_json=_dump([m.model_dump(mode="json") for m in metric_comparisons]),
            regressions_json=_dump([r.model_dump(mode="json") for r in regression_summaries]),
            safety_summary_json=_dump(safety_summary.model_dump(mode="json")),
            reproducibility_summary_json=_dump(reproducibility_summary.model_dump(mode="json")),
            evidence_refs_json=_dump(proof.evidence_refs),
            recommendation=recommendation,
            recommendation_basis_json=_dump(recommendation_basis),
            limitations_json=_dump(limitations),
            content_hash=content_hash,
            generated_at=generated_at,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_proof(self, *, tenant_id: str, proof_id: str) -> ProcessProof:
        row = self.session.query(ProcessProof).filter_by(tenant_id=tenant_id, id=proof_id).one_or_none()
        if row is None:
            raise ProofNotFound(proof_id)
        return row
