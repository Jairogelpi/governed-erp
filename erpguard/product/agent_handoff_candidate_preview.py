from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
)

_GUARD_DISPLAY = {
    "no_generic_writes": "No generic ERP writes",
    "no_r3_r4_writes": "No R3/R4 destructive writes",
    "no_raw_tool_execution": "No raw tool execution",
    "requires_human_review": "Requires human review before execution",
}


@dataclass(frozen=True)
class CandidatePreviewStep:
    step_index: int
    step_id: str
    step_type: str
    description: str


@dataclass(frozen=True)
class HandoffCandidatePreviewResult:
    packet_id: str
    draft_id: str
    proposal_id: str
    preview_skill_id: str
    preview_version_name: str
    steps: list[CandidatePreviewStep] = field(default_factory=list)
    guard_names: list[str] = field(default_factory=list)
    guard_display: list[str] = field(default_factory=list)
    evidence_summary: dict = field(default_factory=dict)
    readiness_score: int = 0
    would_be_status: str = "candidate"
    candidate_exists: bool = False
    existing_version_id: str | None = None
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def preview_candidate_version(packet_id: str, session) -> HandoffCandidatePreviewResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffCandidatePreviewResult(
            packet_id=packet_id,
            draft_id="",
            proposal_id="",
            preview_skill_id="",
            preview_version_name="",
            blocking_reason="packet_not_found",
        )

    existing_link = get_agent_handoff_version_link_by_packet(session, packet_id)
    packet_data = json.loads(packet.packet_json or "{}")
    sections = {s["section_id"]: s["content"] for s in packet_data.get("sections", [])}

    sections.get("sec_proposal", {})
    draft_data = sections.get("sec_draft", {})
    safety_data = sections.get("sec_safety", {})
    readiness_data = sections.get("sec_readiness", {})

    proposal_id = packet.proposal_id
    draft_id = packet.draft_id
    readiness_score = packet_data.get("readiness_score", readiness_data.get("overall_score", 0))

    skill_id = f"agent_{proposal_id[:16]}" if proposal_id else f"agent_draft_{draft_id[:16]}"
    version_name = f"candidate-from-{draft_id[:12]}"

    guard_names_raw = safety_data.get("guards", {})
    if isinstance(guard_names_raw, dict):
        guard_names = [g["guard_id"] for g in guard_names_raw.get("mandatory_guards", [])]
    elif isinstance(guard_names_raw, list):
        guard_names = guard_names_raw
    else:
        guard_names = ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review"]

    guard_display = [_GUARD_DISPLAY.get(g, g) for g in guard_names]

    workflow_steps_raw = draft_data.get("workflow", {}).get("steps", [])
    steps = [
        CandidatePreviewStep(
            step_index=i,
            step_id=s.get("id", f"step_{i}"),
            step_type=s.get("type", "unknown"),
            description=s.get("description", s.get("name", f"Step {i + 1}")),
        )
        for i, s in enumerate(workflow_steps_raw)
    ]
    if not steps:
        steps = [CandidatePreviewStep(
            step_index=0, step_id="advisory_step_0",
            step_type="advisory", description="Agent advisory workflow (no executable steps)",
        )]

    bridge_data = sections.get("sec_bridge", {})
    evidence_summary = {
        "bridge_review": bridge_data.get("review", "unknown"),
        "bridge_validation": bridge_data.get("validation", "unknown"),
        "bridge_compile_plan": bridge_data.get("compile_plan", "unknown"),
        "readiness_score": readiness_score,
        "ready_for_review": packet_data.get("ready_for_review", False),
    }

    return HandoffCandidatePreviewResult(
        packet_id=packet_id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        preview_skill_id=skill_id,
        preview_version_name=version_name,
        steps=steps,
        guard_names=guard_names,
        guard_display=guard_display,
        evidence_summary=evidence_summary,
        readiness_score=readiness_score,
        would_be_status="candidate",
        candidate_exists=existing_link is not None,
        existing_version_id=existing_link.version_id if existing_link else None,
    )
