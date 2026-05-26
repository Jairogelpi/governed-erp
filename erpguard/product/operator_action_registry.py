from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionRegistryEntry:
    action_key: str
    display_name: str
    description: str
    endpoint_template: str
    method: str
    requires_confirmed_token: bool
    safety_tier: str   # read_only | creates_record | governance_required | activation_only
    allowed: bool = True


_REGISTRY: dict[str, ActionRegistryEntry] = {e.action_key: e for e in [
    ActionRegistryEntry(
        action_key="check_governance_gaps",
        display_name="Check Governance Gaps",
        description="Read-only inspection of unresolved governance requirements for a version.",
        endpoint_template="GET /v1/agent-builder/discovery/gaps/{version_id}",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
    ActionRegistryEntry(
        action_key="record_human_decision",
        display_name="Record Human Decision",
        description="Log an explicit human approval or rejection decision for a candidate version.",
        endpoint_template="POST /v1/agent-candidate-decision/{version_id}",
        method="POST",
        requires_confirmed_token=True,
        safety_tier="governance_required",
    ),
    ActionRegistryEntry(
        action_key="create_activation_request",
        display_name="Create Activation Request",
        description="Submit a formal activation request for a candidate version.",
        endpoint_template="POST /v1/agent-candidate-activation-request/{version_id}",
        method="POST",
        requires_confirmed_token=True,
        safety_tier="governance_required",
    ),
    ActionRegistryEntry(
        action_key="evaluate_final_gate",
        display_name="Evaluate Final Gate",
        description="Run a read-only evaluation of all final governance gates.",
        endpoint_template="GET /v1/agent-builder/advisory/evaluate-final-gate/{version_id}",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
    ActionRegistryEntry(
        action_key="activate_candidate",
        display_name="Activate Candidate",
        description="Promote a fully-governed candidate version to active status.",
        endpoint_template="POST /v1/agent-candidate-activation/{version_id}",
        method="POST",
        requires_confirmed_token=True,
        safety_tier="activation_only",
    ),
    ActionRegistryEntry(
        action_key="run_preview",
        display_name="Run Skill Preview",
        description="Execute a sandboxed, read-only preview run for a skill version.",
        endpoint_template="POST /v1/agent-skill-run-preview/{version_id}/run",
        method="POST",
        requires_confirmed_token=True,
        safety_tier="creates_record",
    ),
    ActionRegistryEntry(
        action_key="search_skills",
        display_name="Search Skills",
        description="Search the governed skill registry by keyword or filter.",
        endpoint_template="GET /v1/agent-builder/discovery/search",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
    ActionRegistryEntry(
        action_key="reuse_suggestions",
        display_name="Get Reuse Suggestions",
        description="Retrieve ranked reuse suggestions for a version or goal.",
        endpoint_template="GET /v1/agent-builder/discovery/reuse",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
    ActionRegistryEntry(
        action_key="inspect_lifecycle",
        display_name="Inspect Lifecycle",
        description="Retrieve the full lifecycle summary and governance status for a version.",
        endpoint_template="GET /v1/agent-builder/advisory/lifecycle-summary/{version_id}",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
    ActionRegistryEntry(
        action_key="recommend_next_step",
        display_name="Recommend Next Step",
        description="Return ordered advisory next-step recommendations for a version.",
        endpoint_template="GET /v1/agent-builder/discovery/recommendations/{version_id}",
        method="GET",
        requires_confirmed_token=False,
        safety_tier="read_only",
    ),
]}


# Normalization: maps fragments in endpoint_hint → canonical action_key
_NORMALIZATION_RULES: list[tuple[str, str, str]] = [
    # (method_pattern, hint_fragment, action_key) — method_pattern "" matches any
    ("POST", "candidate-activation-request", "create_activation_request"),
    ("POST", "activation-request", "create_activation_request"),
    ("POST", "candidate-activation", "activate_candidate"),
    ("POST", "decision", "record_human_decision"),
    ("POST", "run-preview", "run_preview"),
    ("POST", "skill-run-preview", "run_preview"),
    ("", "final-gate", "evaluate_final_gate"),
    ("", "evaluate-final-gate", "evaluate_final_gate"),
    ("", "discovery/gaps", "check_governance_gaps"),
    ("GET", "gaps", "check_governance_gaps"),
    ("", "lifecycle-summary", "inspect_lifecycle"),
    ("", "lifecycle", "inspect_lifecycle"),
    ("", "recommendations", "recommend_next_step"),
    ("", "next-step", "recommend_next_step"),
    ("", "discovery/reuse", "reuse_suggestions"),
    ("", "reuse", "reuse_suggestions"),
    ("", "discovery/search", "search_skills"),
    ("", "discovery/similar", "search_skills"),
    ("GET", "search", "search_skills"),
]


def normalize_to_action_key(endpoint_hint: str, method: str = "") -> str | None:
    lower = endpoint_hint.lower()
    method_upper = method.upper()
    for rule_method, fragment, key in _NORMALIZATION_RULES:
        if fragment in lower:
            if not rule_method or rule_method == method_upper:
                return key
    return None


def get_action_entry(action_key: str) -> ActionRegistryEntry | None:
    return _REGISTRY.get(action_key)


def list_all_actions() -> list[ActionRegistryEntry]:
    return list(_REGISTRY.values())
