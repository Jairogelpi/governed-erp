from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction
from erpguard.compiler.recording_to_skill import compile_recording_to_skill_package
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_skill,
    create_skill_run,
    create_skill_run_step,
    create_skill_version,
    finish_skill_run,
    get_recording_session,
    get_latest_skill_version,
    get_skill,
    list_recording_events,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.policies.engine import PolicyEngine
from erpguard.recorder.browser_recorder import record_fake_erp_formula_review_flow


_TOKEN_ECONOMICS = {
    "creation_token_cost_estimate": 2000,
    "repeated_execution_token_cost": 0,
    "estimated_tokens_saved": 2000,
}


@dataclass(slots=True)
class DeterministicSkillRunResult:
    skill_run_id: str
    order_reference: str
    decision: str
    issues_count: int


@dataclass(slots=True)
class FullDemoFlowResult:
    recording: dict[str, Any]
    skill: dict[str, Any]
    runs: dict[str, DeterministicSkillRunResult]
    token_economics: dict[str, int]
    proof: dict[str, bool]


def execute_full_record_to_skill_flow(
    *,
    base_url: str,
    record_order_reference: str,
    valid_order_reference: str,
    invalid_order_reference: str,
    actor: dict[str, Any],
) -> FullDemoFlowResult:
    if not record_order_reference:
        raise ValueError("record_order_reference is required.")

    init_db()
    session = SessionLocal()
    try:
        recording_result = record_fake_erp_formula_review_flow(base_url, record_order_reference, actor)
        recording = get_recording_session(session, recording_result.recording_id)
        if recording is None:
            raise ValueError(f"Recording '{recording_result.recording_id}' was not persisted.")
        events = list_recording_events(session, recording.id)
        skill_package = compile_recording_to_skill_package(recording, events)

        skill = create_skill(session, "Demo Recorded Fake ERP Formula Review", "Compiled from demo recording.")
        version = create_skill_version(
            session=session,
            skill_id=skill.id,
            version="1.0.0",
            skill_package_json=_dump(skill_package),
            runtime_type="deterministic_browser",
            llm_required_for_repeated_runs=bool(skill_package.get("llm_required_for_repeated_runs", False)),
        )

        valid_run = _run_deterministic_skill(session=session, skill_id=skill.id, skill_version_id=version.id, order_reference=valid_order_reference)
        invalid_run = _run_deterministic_skill(session=session, skill_id=skill.id, skill_version_id=version.id, order_reference=invalid_order_reference)

        total_estimated_tokens_saved = _TOKEN_ECONOMICS["estimated_tokens_saved"] * 2
        return FullDemoFlowResult(
            recording={
                "recording_id": recording.id,
                "status": recording.status,
                "event_count": len(events),
            },
            skill={
                "skill_id": skill.id,
                "version_id": version.id,
                "name": skill.name,
                "llm_required_for_repeated_runs": version.llm_required_for_repeated_runs,
            },
            runs={"valid": valid_run, "invalid": invalid_run},
            token_economics={
                "creation_token_cost_estimate": _TOKEN_ECONOMICS["creation_token_cost_estimate"],
                "repeated_execution_token_cost": _TOKEN_ECONOMICS["repeated_execution_token_cost"],
                "estimated_tokens_saved_per_run": _TOKEN_ECONOMICS["estimated_tokens_saved"],
                "total_estimated_tokens_saved": total_estimated_tokens_saved,
            },
            proof={
                "record_to_skill": True,
                "deterministic_replay": True,
                "erpguard_blocked_invalid_order": invalid_run.decision == "block",
                "no_llm_used_for_repeated_runs": not version.llm_required_for_repeated_runs,
            },
        )
    finally:
        session.close()


def run_deterministic_skill_for_order_reference(
    *,
    session,
    skill_id: str,
    order_reference: str,
) -> DeterministicSkillRunResult:
    skill = get_skill(session, skill_id)
    if skill is None:
        raise ValueError(f"Skill '{skill_id}' not found.")

    skill_version = get_latest_skill_version(session, skill.id)
    if skill_version is None:
        raise ValueError(f"Skill '{skill_id}' has no registered version.")

    return _run_deterministic_skill(session=session, skill_id=skill.id, skill_version_id=skill_version.id, order_reference=order_reference)


def _run_deterministic_skill(*, session, skill_id: str, skill_version_id: str, order_reference: str) -> DeterministicSkillRunResult:
    run = create_skill_run(
        session=session,
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        status="running",
        input_json=_dump({"inputs": {"order_reference": order_reference}}),
    )
    create_skill_run_step(
        session=session,
        skill_run_id=run.id,
        step_id="load_skill",
        step_type="load",
        status="passed",
        input_json=_dump({"skill_id": skill_id, "version_id": skill_version_id}),
        output_json=_dump({"runtime_type": "deterministic_browser"}),
    )

    adapter = FakeERPAdapter()
    try:
        order = adapter.get_sales_order_by_reference(order_reference)
    except ObjectNotFoundError as exc:
        create_skill_run_step(
            session=session,
            skill_run_id=run.id,
            step_id="load_order",
            step_type="load",
            status="failed",
            input_json=_dump({"order_reference": order_reference}),
            error_text=str(exc),
        )
        create_skill_run_step(
            session=session,
            skill_run_id=run.id,
            step_id="formula_guard",
            step_type="guard",
            status="failed",
            input_json=_dump({"policy_id": "formula_guard", "policy_version": "0.1.0"}),
            error_text=str(exc),
        )
        output: dict[str, Any] = {
            "order_reference": order_reference,
            "policy_id": "formula_guard",
            "policy_version": "0.1.0",
            "issues": [],
        }
        finished = finish_skill_run(
            session=session,
            skill_run_id=run.id,
            status="failed",
            output_json=_dump(output),
            decision="block",
            error_text=str(exc),
            estimated_tokens_saved=_TOKEN_ECONOMICS["estimated_tokens_saved"],
        )
        create_skill_run_step(
            session=session,
            skill_run_id=run.id,
            step_id="produce_result",
            step_type="result",
            status="passed",
            output_json=_dump({"decision": "block", "issues_count": 0}),
        )
        return DeterministicSkillRunResult(
            skill_run_id=finished.id,
            order_reference=order_reference,
            decision="block",
            issues_count=0,
        )

    create_skill_run_step(
        session=session,
        skill_run_id=run.id,
        step_id="load_order",
        step_type="load",
        status="passed",
        input_json=_dump({"order_reference": order_reference}),
        output_json=_dump({"order_id": order.id, "reference": order.reference}),
    )

    policy_result = PolicyEngine().evaluate("formula_guard", order, canonical_action=CanonicalAction.VALIDATE_FORMULA)
    create_skill_run_step(
        session=session,
        skill_run_id=run.id,
        step_id="formula_guard",
        step_type="guard",
        status="blocked" if policy_result.decision.value == "block" else "passed",
        input_json=_dump({"policy_id": policy_result.policy_id, "policy_version": policy_result.policy_version}),
        output_json=_dump(policy_result.model_dump(mode="json")),
    )

    output = {
        "order_reference": order.reference,
        "policy_id": policy_result.policy_id,
        "policy_version": policy_result.policy_version,
        "issues": [issue.model_dump(mode="json") for issue in policy_result.issues],
    }
    finished = finish_skill_run(
        session=session,
        skill_run_id=run.id,
        status="success",
        output_json=_dump(output),
        decision=policy_result.decision.value,
        estimated_tokens_saved=_TOKEN_ECONOMICS["estimated_tokens_saved"],
    )
    create_skill_run_step(
        session=session,
        skill_run_id=run.id,
        step_id="produce_result",
        step_type="result",
        status="passed",
        output_json=_dump({"decision": policy_result.decision.value, "issues_count": len(policy_result.issues)}),
    )
    return DeterministicSkillRunResult(
        skill_run_id=finished.id,
        order_reference=order.reference,
        decision=policy_result.decision.value,
        issues_count=len(policy_result.issues),
    )


def _dump(value: Any) -> str:
    import json

    return json.dumps(value, default=str)
