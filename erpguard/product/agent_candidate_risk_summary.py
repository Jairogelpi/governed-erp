from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record

_RISK_LABELS = {
    "agent_advisory": "Agent-sourced advisory skill — human review mandatory",
    "deterministic_ui": "Deterministic UI skill — standard promotion flow",
}

_GUARD_RISK = {
    "no_generic_writes": "low",
    "no_r3_r4_writes": "low",
    "no_raw_tool_execution": "low",
    "requires_human_review": "low",
    "guard_read_only": "low",
    "guard_amount_limit": "medium",
}


@dataclass(frozen=True)
class AgentCandidateRiskSummaryResult:
    version_id: str
    skill_id: str
    runtime_type: str
    runtime_label: str
    llm_required: bool
    guard_names: list[str]
    guard_count: int
    risk_level: str
    risk_flags: list[str] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def get_risk_summary(version_id: str, session) -> AgentCandidateRiskSummaryResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateRiskSummaryResult(
            version_id=version_id,
            skill_id="",
            runtime_type="unknown",
            runtime_label="Version not found",
            llm_required=False,
            guard_names=[],
            guard_count=0,
            risk_level="unknown",
            blocking_reason="version_not_found",
        )

    guard_names: list[str] = json.loads(version_row.guard_names_json or "[]")
    runtime_type = version_row.runtime_type
    llm_required = version_row.llm_required

    risk_flags: list[str] = []

    if runtime_type == "agent_advisory":
        risk_flags.append("agent_sourced: mandatory human review before any promotion")
    if llm_required:
        risk_flags.append("llm_required: LLM in loop — requires additional scrutiny")
    if not guard_names:
        risk_flags.append("no_guards: no safety guards declared — review carefully")

    risk_level = "low"
    if llm_required:
        risk_level = "medium"
    if runtime_type not in ("agent_advisory", "deterministic_ui"):
        risk_level = "high"

    return AgentCandidateRiskSummaryResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        runtime_type=runtime_type,
        runtime_label=_RISK_LABELS.get(runtime_type, runtime_type),
        llm_required=llm_required,
        guard_names=guard_names,
        guard_count=len(guard_names),
        risk_level=risk_level,
        risk_flags=risk_flags,
    )
