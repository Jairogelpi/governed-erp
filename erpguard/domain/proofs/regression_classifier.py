"""Regression classification between two replay runs (master spec section 16).

This codebase has exactly one real policy evaluator (`formula_guard`,
binary block/allow). Only four of the spec's eleven regression categories
(16.1) are genuinely detectable here, by comparing a baseline case's
per-decision outcome against the matching candidate case's:

- `new_unsafe_effect` (severity `critical`): a decision the baseline BLOCKED
  (had safety violations) is now ALLOWED by the candidate for the same
  case/decision. An effect the baseline correctly stopped now passes
  through unblocked -- this is the one transition that cleanly maps onto
  spec 16.2's "effect forbidden by policy" critical example. This is the
  ONLY transition this classifier ever marks `critical`.
- `false_block` (severity `low`): the reverse transition, baseline ALLOWED,
  candidate BLOCKS the same decision. There is no ground truth here to know
  whether the new block is a genuine false positive or the candidate
  correctly catching something the baseline missed, so it is never treated
  as an automatic improvement -- it's surfaced as a low-severity item for
  human review, not silently dropped.
- `evidence_incompleteness` (severity `medium`): one side's case status is
  `needs_clarification` and the other isn't -- a case that used to produce
  a real result no longer can, or vice versa.
- `postcondition_failure` (severity `medium`): both sides blocked the same
  decision, but the set of violation codes differs -- the failure mode
  itself changed even though both sides "failed".

The remaining spec 16.1 categories (`newly_incorrect_entity_resolution`,
`duplicate_creation`, `missing_approval`, `additional_approval`,
`incompatible_fingerprint`, `latency_threshold_breach`, `token_increase`)
have no detector in this codebase -- they are never emitted. A future
evaluator (entity resolution, duplicate detection, latency/token metrics,
approval-count tracking) would be needed before those could be real.
"""

from __future__ import annotations

from typing import Any, TypedDict

from erpguard.domain.proofs.types import RegressionSummary


class CaseDetail(TypedDict):
    case_id: str
    category: str
    severity: str
    decision_name: str


def _decisions_by_name(decision_trace: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["decision_name"]: item for item in decision_trace}


def _violation_codes(safety_violations: list[dict[str, Any]], decision_name: str) -> frozenset[str]:
    # safety_violations aren't decision-scoped in the stored shape, so for a
    # single-evaluator engine (only formula_guard exists today) all recorded
    # violations belong to the one blocking decision present in the trace.
    return frozenset(item["code"] for item in safety_violations)


def classify_case_pair(
    *,
    case_id: str,
    baseline_status: str,
    baseline_decision_trace: list[dict[str, Any]],
    baseline_safety_violations: list[dict[str, Any]],
    candidate_status: str,
    candidate_decision_trace: list[dict[str, Any]],
    candidate_safety_violations: list[dict[str, Any]],
) -> list[CaseDetail]:
    details: list[CaseDetail] = []

    if baseline_status == "needs_clarification" and candidate_status != "needs_clarification":
        details.append(
            CaseDetail(case_id=case_id, category="evidence_incompleteness", severity="medium", decision_name="")
        )
    elif candidate_status == "needs_clarification" and baseline_status != "needs_clarification":
        details.append(
            CaseDetail(case_id=case_id, category="evidence_incompleteness", severity="medium", decision_name="")
        )

    if baseline_status == "needs_clarification" or candidate_status == "needs_clarification":
        return details

    baseline_decisions = _decisions_by_name(baseline_decision_trace)
    candidate_decisions = _decisions_by_name(candidate_decision_trace)

    for decision_name in sorted(set(baseline_decisions) & set(candidate_decisions)):
        b_outcome = baseline_decisions[decision_name]["outcome"]
        c_outcome = candidate_decisions[decision_name]["outcome"]

        if b_outcome == "block" and c_outcome == "allow":
            details.append(
                CaseDetail(case_id=case_id, category="new_unsafe_effect", severity="critical", decision_name=decision_name)
            )
        elif b_outcome == "allow" and c_outcome == "block":
            details.append(
                CaseDetail(case_id=case_id, category="false_block", severity="low", decision_name=decision_name)
            )
        elif b_outcome == "block" and c_outcome == "block":
            b_codes = _violation_codes(baseline_safety_violations, decision_name)
            c_codes = _violation_codes(candidate_safety_violations, decision_name)
            if b_codes != c_codes:
                details.append(
                    CaseDetail(
                        case_id=case_id, category="postcondition_failure", severity="medium", decision_name=decision_name
                    )
                )

    return details


def classify_regressions(
    case_pairs: list[dict[str, Any]],
) -> tuple[list[RegressionSummary], list[CaseDetail]]:
    """`case_pairs` items: {case_id, baseline_status, baseline_decision_trace,
    baseline_safety_violations, candidate_status, candidate_decision_trace,
    candidate_safety_violations}. Returns (grouped summaries, per-case details).
    """

    all_details: list[CaseDetail] = []
    for pair in case_pairs:
        all_details.extend(classify_case_pair(**pair))

    counts: dict[tuple[str, str], int] = {}
    for detail in all_details:
        key = (detail["severity"], detail["category"])
        counts[key] = counts.get(key, 0) + 1

    summaries = [
        RegressionSummary(severity=severity, category=category, count=count)  # type: ignore[arg-type]
        for (severity, category), count in sorted(counts.items())
    ]
    return summaries, all_details
