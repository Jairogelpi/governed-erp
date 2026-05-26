from __future__ import annotations

from dataclasses import dataclass

from erpguard.product.operator_action_registry import ActionRegistryEntry


@dataclass(frozen=True)
class PolicyCheckResult:
    allowed: bool
    reason: str
    policy_name: str


def check_dispatch_policy(
    entry: ActionRegistryEntry,
    *,
    token_confirmed: bool,
    version_id: str | None = None,
) -> PolicyCheckResult:
    """Evaluate safety policy for an allowlisted action. No mutations, no execution."""

    # Tier: activation_only — strictest tier, requires confirmed token always
    if entry.safety_tier == "activation_only":
        if not token_confirmed:
            return PolicyCheckResult(
                allowed=False,
                reason=(
                    f"Action '{entry.action_key}' is in the activation_only safety tier. "
                    "A confirmed operator token is mandatory before eligibility can be granted."
                ),
                policy_name="activation_tier_requires_token",
            )
        return PolicyCheckResult(
            allowed=True,
            reason=f"Activation action '{entry.action_key}' has a confirmed token. Eligible for operator dispatch.",
            policy_name="activation_tier_token_confirmed",
        )

    # Tier: governance_required — requires confirmed token
    if entry.safety_tier == "governance_required":
        if not token_confirmed:
            return PolicyCheckResult(
                allowed=False,
                reason=(
                    f"Action '{entry.action_key}' requires governance review. "
                    "A confirmed operator token is required."
                ),
                policy_name="governance_tier_requires_token",
            )
        return PolicyCheckResult(
            allowed=True,
            reason=f"Governance action '{entry.action_key}' token confirmed. Eligible.",
            policy_name="governance_tier_token_confirmed",
        )

    # Tier: creates_record — requires confirmed token
    if entry.safety_tier == "creates_record":
        if not token_confirmed:
            return PolicyCheckResult(
                allowed=False,
                reason=(
                    f"Action '{entry.action_key}' creates an audit record. "
                    "Operator must confirm the token before dispatch."
                ),
                policy_name="creates_record_requires_token",
            )
        return PolicyCheckResult(
            allowed=True,
            reason=f"Record-creating action '{entry.action_key}' token confirmed. Eligible.",
            policy_name="creates_record_token_confirmed",
        )

    # Tier: read_only — always eligible, no token required
    return PolicyCheckResult(
        allowed=True,
        reason=f"Read-only action '{entry.action_key}' is always eligible. No token required.",
        policy_name="read_only_always_eligible",
    )
