from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import get_action_plan_step_token
from erpguard.product.operator_action_dispatch_policy import check_dispatch_policy
from erpguard.product.operator_action_registry import (
    ActionRegistryEntry,
    get_action_entry,
    normalize_to_action_key,
)


@dataclass
class DispatchEligibilityResult:
    action_key: str
    endpoint_hint: str
    eligible: bool
    blocked_reason: str | None
    policy_name: str | None
    requires_confirmed_token: bool
    safety_tier: str
    token_id: str | None
    token_status: str | None
    version_id: str | None
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def check_eligibility(
    *,
    action_key: str | None,
    endpoint_hint: str,
    method_hint: str,
    token_id: str | None,
    version_id: str | None,
    session,
) -> DispatchEligibilityResult:
    """
    Evaluate dispatch eligibility for a plan step. Read-only — no mutations.
    Returns an eligibility result; never executes the action.
    """
    # Step 1: resolve action_key
    resolved_key = action_key or normalize_to_action_key(endpoint_hint, method_hint)

    if not resolved_key:
        return DispatchEligibilityResult(
            action_key="unknown",
            endpoint_hint=endpoint_hint,
            eligible=False,
            blocked_reason=(
                "Endpoint hint could not be normalized to a known action key. "
                "Only registry-defined action keys may pass validation."
            ),
            policy_name="unknown_action_key",
            requires_confirmed_token=False,
            safety_tier="unknown",
            token_id=token_id,
            token_status=None,
            version_id=version_id,
        )

    # Step 2: registry lookup
    entry: ActionRegistryEntry | None = get_action_entry(resolved_key)
    if entry is None:
        return DispatchEligibilityResult(
            action_key=resolved_key,
            endpoint_hint=endpoint_hint,
            eligible=False,
            blocked_reason=(
                f"Action key '{resolved_key}' is not in the allowlist registry. "
                "Only explicitly registered actions may be dispatched."
            ),
            policy_name="not_in_registry",
            requires_confirmed_token=False,
            safety_tier="unknown",
            token_id=token_id,
            token_status=None,
            version_id=version_id,
        )

    # Step 3: resolve token status
    token_status: str | None = None
    token_confirmed = False
    if token_id:
        row = get_action_plan_step_token(session, token_id)
        if row:
            token_status = row.status
            token_confirmed = row.status == "confirmed"

    # If action requires token but none provided
    if entry.requires_confirmed_token and not token_id:
        return DispatchEligibilityResult(
            action_key=resolved_key,
            endpoint_hint=endpoint_hint,
            eligible=False,
            blocked_reason=(
                f"Action '{resolved_key}' requires a confirmed operator token. "
                "No token_id was provided."
            ),
            policy_name="token_required_not_provided",
            requires_confirmed_token=True,
            safety_tier=entry.safety_tier,
            token_id=None,
            token_status=None,
            version_id=version_id,
        )

    # Step 4: policy check
    policy = check_dispatch_policy(entry, token_confirmed=token_confirmed, version_id=version_id)

    return DispatchEligibilityResult(
        action_key=resolved_key,
        endpoint_hint=endpoint_hint,
        eligible=policy.allowed,
        blocked_reason=None if policy.allowed else policy.reason,
        policy_name=policy.policy_name,
        requires_confirmed_token=entry.requires_confirmed_token,
        safety_tier=entry.safety_tier,
        token_id=token_id,
        token_status=token_status,
        version_id=version_id,
    )
