"""Spec 92 Sec 9.9 -- promotion hardening.

Canary status alone was never sufficient once a policy exists for the
package; this is the check `SkillDeploymentService.promote_to_active`
calls when a `CanaryPolicy` names the package being promoted.
"""

from __future__ import annotations

MINIMUM_CANARY_CASES = 10
MINIMUM_POSTCONDITION_SUCCESS_RATE = 0.9
MINIMUM_OBSERVATION_COVERAGE = 0.8


def check_promotion_eligibility(
    *,
    policy_status: str,
    unresolved_critical_incidents: int,
    canary_case_count: int,
    postcondition_success_rate: float | None,
    observation_coverage: float | None,
) -> list[str]:
    """Returns violated preconditions; empty list means eligible."""

    issues: list[str] = []
    if policy_status != "completed":
        issues.append(f"canary_policy_not_completed:{policy_status}")
    if unresolved_critical_incidents > 0:
        issues.append(f"unresolved_critical_incidents:{unresolved_critical_incidents}")
    if canary_case_count < MINIMUM_CANARY_CASES:
        issues.append(f"insufficient_canary_case_count:{canary_case_count}")
    if postcondition_success_rate is None or postcondition_success_rate < MINIMUM_POSTCONDITION_SUCCESS_RATE:
        issues.append(f"insufficient_postcondition_success_rate:{postcondition_success_rate}")
    if observation_coverage is None or observation_coverage < MINIMUM_OBSERVATION_COVERAGE:
        issues.append(f"insufficient_observation_coverage:{observation_coverage}")
    return issues
