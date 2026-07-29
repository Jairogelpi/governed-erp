"""Proof eligibility rules (master spec 17.3), as far as this codebase can
verify them.

Two of the spec's seven eligibility criteria are structurally unmeasurable
here and always block anything above `eligible_for_shadow`:

- "duplicate prevention rate meets threshold" -- no duplicate-detection
  logic exists anywhere in this codebase.
- "all required tests pass" -- a CI/test-suite concept, not data available
  at proof-generation time.

"Human reviewer accepts limitations" is out of scope: the spec's
`ProofOfImprovement` model (17.2) has no reviewer-decision field, and this
implementation does not invent an approval workflow -- `recommendation` is
a computed field only.

Given those permanent gaps, this implementation can never recommend
`eligible_for_canary` or `eligible_for_promotion`.
"""

from __future__ import annotations

from erpguard.domain.proofs.types import Recommendation

EVIDENCE_COMPLETENESS_THRESHOLD = 0.9

STRUCTURAL_LIMITATIONS = [
    "Duplicate prevention rate is not measured: no duplicate-detection logic exists in this codebase.",
    "Test-suite pass/fail is not evaluated at proof-generation time.",
    "Synthetic/canonical-event dataset, no causal claim about business outcomes.",
]


def determine_recommendation(
    *,
    critical_regression_count: int,
    evidence_completeness: float,
    reproducible: bool,
) -> tuple[Recommendation, list[str], list[str]]:
    """Returns (recommendation, recommendation_basis, limitations)."""

    limitations = list(STRUCTURAL_LIMITATIONS)

    if critical_regression_count > 0:
        return (
            "reject",
            [f"unresolved_critical_regression_count={critical_regression_count}"],
            limitations,
        )

    if evidence_completeness < EVIDENCE_COMPLETENESS_THRESHOLD:
        return (
            "needs_changes",
            [
                f"evidence_completeness={evidence_completeness:.2f} "
                f"below threshold={EVIDENCE_COMPLETENESS_THRESHOLD:.2f}"
            ],
            limitations,
        )

    if not reproducible:
        return ("needs_changes", ["deterministic_replay_repeatability_failed"], limitations)

    return (
        "eligible_for_shadow",
        [
            "no_unresolved_critical_regression",
            f"evidence_completeness={evidence_completeness:.2f} "
            f"meets threshold={EVIDENCE_COMPLETENESS_THRESHOLD:.2f}",
            "deterministic_replay_repeatability_passed",
        ],
        limitations,
    )
