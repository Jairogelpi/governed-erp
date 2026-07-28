from __future__ import annotations

import uuid
from dataclasses import dataclass

from erpguard.product.operator_action_plan_intent import PlanIntent
from erpguard.product.operator_action_plan_prerequisites import PrerequisiteState
from erpguard.product.operator_action_plan_safety import ActionPlanStep, enforce_safety, safety_summary


@dataclass
class ActionPlan:
    plan_id: str
    plan_type: str
    goal: str
    version_id: str | None
    steps: list[ActionPlanStep]
    total_steps: int
    blocking_count: int
    advisory_summary: str
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def _steps_prepare_for_run(pre: PrerequisiteState, vid: str | None) -> list[ActionPlanStep]:
    v = vid or "{version_id}"
    return [
        ActionPlanStep(
            step_number=1,
            title="Verify version exists",
            description="Confirm the skill version is registered in the system.",
            endpoint_hint=f"GET /v1/agent-builder/versions/{v}",
            method_hint="GET",
            severity="blocking",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version not found — create or register it first.",
        ),
        ActionPlanStep(
            step_number=2,
            title="Check governance gaps",
            description="Identify which governance requirements are still unmet.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/gaps/{v}",
            method_hint="GET",
            severity="blocking",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version must exist before gap analysis.",
        ),
        ActionPlanStep(
            step_number=3,
            title="Record human approval decision",
            description="A human must explicitly approve or reject the candidate version.",
            endpoint_hint=f"POST /v1/agent-candidate-decision/{v}",
            method_hint="POST",
            severity="blocking",
            prereqs_met=pre.has_human_decision and pre.decision_approved,
            blocker_reason=None if (pre.has_human_decision and pre.decision_approved)
                           else "Human approval decision is missing or not yet approved.",
        ),
        ActionPlanStep(
            step_number=4,
            title="Submit activation request",
            description="Operator submits a formal activation request for the version.",
            endpoint_hint=f"POST /v1/agent-candidate-activation-request/{v}",
            method_hint="POST",
            severity="required",
            prereqs_met=pre.has_activation_request,
            blocker_reason=None if pre.has_activation_request else "Activation request has not been submitted.",
        ),
        ActionPlanStep(
            step_number=5,
            title="Evaluate final governance gate",
            description="System evaluates whether all governance gates pass before preview.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/evaluate-final-gate/{v}",
            method_hint="GET",
            severity="required",
            prereqs_met=pre.has_human_decision and pre.has_activation_request,
            blocker_reason=None if (pre.has_human_decision and pre.has_activation_request)
                           else "Complete steps 3 and 4 before evaluating the final gate.",
        ),
        ActionPlanStep(
            step_number=6,
            title="Run skill preview",
            description="Execute a safe, sandboxed preview run. Operator must click to confirm.",
            endpoint_hint=f"POST /v1/agent-skill-run-preview/{v}/run",
            method_hint="POST",
            severity="required",
            prereqs_met=False,
            blocker_reason="Operator must explicitly click to trigger preview — never automatic.",
        ),
    ]


def _steps_activate_candidate(pre: PrerequisiteState, vid: str | None) -> list[ActionPlanStep]:
    v = vid or "{version_id}"
    return [
        ActionPlanStep(
            step_number=1,
            title="Confirm candidate is approved",
            description="Verify a human decision with status 'approved' exists for this version.",
            endpoint_hint=f"GET /v1/agent-candidate-approval/{v}",
            method_hint="GET",
            severity="blocking",
            prereqs_met=pre.decision_approved,
            blocker_reason=None if pre.decision_approved else "No approved human decision found.",
        ),
        ActionPlanStep(
            step_number=2,
            title="Verify activation request submitted",
            description="Confirm a formal activation request has been recorded.",
            endpoint_hint=f"GET /v1/agent-candidate-activation-request/{v}",
            method_hint="GET",
            severity="blocking",
            prereqs_met=pre.has_activation_request,
            blocker_reason=None if pre.has_activation_request else "Activation request is missing.",
        ),
        ActionPlanStep(
            step_number=3,
            title="Evaluate final governance gate",
            description="All governance gates must pass before the activation is allowed.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/evaluate-final-gate/{v}",
            method_hint="GET",
            severity="blocking",
            prereqs_met=pre.decision_approved and pre.has_activation_request,
            blocker_reason=None if (pre.decision_approved and pre.has_activation_request)
                           else "Complete governance steps before gate evaluation.",
        ),
        ActionPlanStep(
            step_number=4,
            title="Trigger candidate activation",
            description="Operator explicitly activates the candidate. Requires operator click.",
            endpoint_hint=f"POST /v1/agent-candidate-activation/{v}",
            method_hint="POST",
            severity="required",
            prereqs_met=False,
            blocker_reason="Operator must explicitly click to activate — never automatic.",
        ),
    ]


def _steps_fix_governance_gaps(pre: PrerequisiteState, vid: str | None) -> list[ActionPlanStep]:
    v = vid or "{version_id}"
    gap_map = {
        "no_human_decision": ActionPlanStep(
            step_number=0,
            title="Record human decision",
            description="A human reviewer must log an approval or rejection decision.",
            endpoint_hint=f"POST /v1/agent-candidate-decision/{v}",
            method_hint="POST",
            severity="blocking",
            prereqs_met=False,
            blocker_reason="Human decision is absent.",
        ),
        "decision_not_approved": ActionPlanStep(
            step_number=0,
            title="Obtain approved decision",
            description="Existing decision must be updated to 'approved' status.",
            endpoint_hint=f"POST /v1/agent-candidate-decision/{v}",
            method_hint="POST",
            severity="blocking",
            prereqs_met=False,
            blocker_reason="Decision exists but is not approved.",
        ),
        "no_activation_request": ActionPlanStep(
            step_number=0,
            title="Submit activation request",
            description="Formal activation request must be submitted by the operator.",
            endpoint_hint=f"POST /v1/agent-candidate-activation-request/{v}",
            method_hint="POST",
            severity="required",
            prereqs_met=False,
            blocker_reason="Activation request is missing.",
        ),
        "final_gate_not_evaluated": ActionPlanStep(
            step_number=0,
            title="Evaluate final gate",
            description="Trigger a final gate evaluation to surface remaining blockers.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/evaluate-final-gate/{v}",
            method_hint="GET",
            severity="required",
            prereqs_met=False,
            blocker_reason="Final gate has not been evaluated.",
        ),
        "preview_not_run": ActionPlanStep(
            step_number=0,
            title="Run preview",
            description="At least one preview run must be logged before activation.",
            endpoint_hint=f"POST /v1/agent-skill-run-preview/{v}/run",
            method_hint="POST",
            severity="required",
            prereqs_met=False,
            blocker_reason="No preview run recorded.",
        ),
        "not_activated": ActionPlanStep(
            step_number=0,
            title="Activate the version",
            description="Version is not yet active — complete prior steps then activate.",
            endpoint_hint=f"POST /v1/agent-candidate-activation/{v}",
            method_hint="POST",
            severity="optional",
            prereqs_met=False,
            blocker_reason="Version still in candidate state.",
        ),
    }
    base = [
        ActionPlanStep(
            step_number=1,
            title="Fetch governance gaps",
            description="Retrieve the current list of unresolved governance gaps.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/gaps/{v}",
            method_hint="GET",
            severity="required",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version not found.",
        ),
    ]
    gap_steps = [gap_map[g] for g in pre.governance_gaps if g in gap_map]
    for i, step in enumerate(gap_steps, start=2):
        step.step_number = i
    return base + gap_steps if gap_steps else base + [
        ActionPlanStep(
            step_number=2,
            title="No unresolved gaps found",
            description="All governance requirements appear to be met for this version.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/evaluate-final-gate/{v}",
            method_hint="GET",
            severity="optional",
            prereqs_met=True,
        ),
    ]


def _steps_find_reusable_skill(pre: PrerequisiteState, vid: str | None) -> list[ActionPlanStep]:
    v = vid or "{version_id}"
    return [
        ActionPlanStep(
            step_number=1,
            title="Search active skill registry",
            description="Query the registry for active skills by keyword.",
            endpoint_hint="GET /v1/agent-builder/discovery/search?query=…",
            method_hint="GET",
            severity="required",
            prereqs_met=True,
        ),
        ActionPlanStep(
            step_number=2,
            title="Get reuse suggestions",
            description="Retrieve ranked reuse suggestions for the target version or goal.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/reuse?version_id={v}",
            method_hint="GET",
            severity="required",
            prereqs_met=True,
        ),
        ActionPlanStep(
            step_number=3,
            title="Find similar versions",
            description="Identify structurally similar skill versions using Jaccard similarity.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/similar/{v}",
            method_hint="GET",
            severity="optional",
            prereqs_met=pre.version_exists or not vid,
            blocker_reason=None if (pre.version_exists or not vid) else "Provide a valid version_id for similarity matching.",
        ),
        ActionPlanStep(
            step_number=4,
            title="Operator decides to fork or adapt",
            description="If a reusable skill is found, operator manually decides to adopt it.",
            endpoint_hint="(operator decision — no automatic action)",
            method_hint="NONE",
            severity="optional",
            prereqs_met=False,
            blocker_reason="Operator must decide and act — never automatic.",
        ),
    ]


def _steps_inspect_lifecycle(pre: PrerequisiteState, vid: str | None) -> list[ActionPlanStep]:
    v = vid or "{version_id}"
    return [
        ActionPlanStep(
            step_number=1,
            title="Get lifecycle summary",
            description="Retrieve the full lifecycle event log and governance status.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/lifecycle-summary/{v}",
            method_hint="GET",
            severity="required",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version not found.",
        ),
        ActionPlanStep(
            step_number=2,
            title="Get governance gaps",
            description="List all unresolved governance requirements.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/gaps/{v}",
            method_hint="GET",
            severity="required",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version must exist.",
        ),
        ActionPlanStep(
            step_number=3,
            title="Get agent recommendations",
            description="Retrieve ordered recommendations from the recommendation engine.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/recommendations/{v}",
            method_hint="GET",
            severity="optional",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version must exist.",
        ),
        ActionPlanStep(
            step_number=4,
            title="Get next steps",
            description="Ask the next-step recommender for the safest immediate action.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/next-steps/{v}",
            method_hint="GET",
            severity="optional",
            prereqs_met=pre.version_exists,
            blocker_reason=None if pre.version_exists else "Version must exist.",
        ),
    ]


def _steps_unknown() -> list[ActionPlanStep]:
    return [
        ActionPlanStep(
            step_number=1,
            title="Clarify operational goal",
            description="Rephrase the goal to match a supported plan type: prepare_for_run, activate_candidate, fix_governance_gaps, find_reusable_skill, or inspect_lifecycle.",
            endpoint_hint="POST /v1/operator-console/action-plan",
            method_hint="POST",
            severity="required",
            prereqs_met=False,
            blocker_reason="Goal could not be classified. Please rephrase.",
        ),
    ]


_BUILDERS = {
    "prepare_for_run": _steps_prepare_for_run,
    "activate_candidate": _steps_activate_candidate,
    "fix_governance_gaps": _steps_fix_governance_gaps,
    "find_reusable_skill": _steps_find_reusable_skill,
    "inspect_lifecycle": _steps_inspect_lifecycle,
}


def build_action_plan(
    intent: PlanIntent,
    goal: str,
    pre: PrerequisiteState,
    version_id: str | None,
) -> ActionPlan:
    plan_id = f"aplan_{uuid.uuid4().hex[:16]}"

    if intent.plan_type in _BUILDERS:
        raw_steps = _BUILDERS[intent.plan_type](pre, version_id)
    else:
        raw_steps = _steps_unknown()

    steps = enforce_safety(raw_steps)
    blocking = sum(1 for s in steps if s.severity == "blocking" and not s.prereqs_met)
    summary = safety_summary(steps)

    return ActionPlan(
        plan_id=plan_id,
        plan_type=intent.plan_type,
        goal=goal,
        version_id=version_id,
        steps=steps,
        total_steps=len(steps),
        blocking_count=blocking,
        advisory_summary=summary,
    )
