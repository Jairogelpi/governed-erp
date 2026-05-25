from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    create_agent_handoff_version_event,
    create_agent_handoff_version_link,
    create_ui_skill_version_lifecycle_event,
    create_ui_skill_version_record,
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
    get_ui_skill_version_record,
    update_ui_skill_version_status,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class HandoffCandidateResult:
    packet_id: str
    version_id: str
    skill_id: str
    version_number: int
    status: str
    draft_id: str
    proposal_id: str
    is_cached: bool = False
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def create_candidate_version(packet_id: str, session) -> HandoffCandidateResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffCandidateResult(
            packet_id=packet_id, version_id="", skill_id="",
            version_number=0, status="blocked",
            draft_id="", proposal_id="",
            blocking_reason="packet_not_found",
        )

    existing_link = get_agent_handoff_version_link_by_packet(session, packet_id)
    if existing_link is not None:
        version_row = get_ui_skill_version_record(session, existing_link.version_id)
        return HandoffCandidateResult(
            packet_id=packet_id,
            version_id=existing_link.version_id,
            skill_id=existing_link.skill_id,
            version_number=version_row.version_number if version_row else 0,
            status=version_row.status if version_row else "candidate",
            draft_id=packet.draft_id,
            proposal_id=packet.proposal_id,
            is_cached=True,
        )

    packet_data = json.loads(packet.packet_json or "{}")
    sections = {s["section_id"]: s["content"] for s in packet_data.get("sections", [])}
    draft_data = sections.get("sec_draft", {})
    safety_data = sections.get("sec_safety", {})

    proposal_id = packet.proposal_id
    draft_id = packet.draft_id
    skill_id = f"agent_{proposal_id[:16]}" if proposal_id else f"agent_draft_{draft_id[:16]}"
    version_name = f"candidate-from-{draft_id[:12]}"

    guard_names_raw = safety_data.get("guards", {})
    if isinstance(guard_names_raw, dict):
        guard_names = [g["guard_id"] for g in guard_names_raw.get("mandatory_guards", [])]
    else:
        guard_names = ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review"]

    workflow_steps = draft_data.get("workflow", {}).get("steps", [])
    if not workflow_steps:
        workflow_steps = [{"id": "advisory_step_0", "type": "advisory",
                           "description": "Agent advisory workflow"}]

    steps_json = json.dumps(workflow_steps)
    guard_names_json = json.dumps(guard_names)
    compiled_skill_id = f"agent_draft_{draft_id[:16]}"

    version_row = create_ui_skill_version_record(
        session,
        skill_id=skill_id,
        compiled_skill_id=compiled_skill_id,
        name=version_name,
        steps_json=steps_json,
        guard_names_json=guard_names_json,
        runtime_type="agent_advisory",
        llm_required=False,
    )
    create_ui_skill_version_lifecycle_event(
        session,
        version_id=version_row.id,
        skill_id=skill_id,
        event_type="created",
        from_status="none",
        to_status="draft",
        actor="agent_handoff",
        reason=f"created_from_handoff_packet:{packet_id}",
    )

    update_ui_skill_version_status(session, version_row.id, status="candidate", is_active=False)
    create_ui_skill_version_lifecycle_event(
        session,
        version_id=version_row.id,
        skill_id=skill_id,
        event_type="promote_candidate",
        from_status="draft",
        to_status="candidate",
        actor="agent_handoff",
        reason=f"promoted_from_handoff_packet:{packet_id}",
    )

    create_agent_handoff_version_link(
        session,
        packet_id=packet_id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        version_id=version_row.id,
        skill_id=skill_id,
    )

    create_agent_handoff_version_event(
        session, packet_id, "create_candidate",
        "completed",
        json.dumps({"version_id": version_row.id, "skill_id": skill_id, "status": "candidate"}),
    )

    return HandoffCandidateResult(
        packet_id=packet_id,
        version_id=version_row.id,
        skill_id=skill_id,
        version_number=version_row.version_number,
        status="candidate",
        draft_id=draft_id,
        proposal_id=proposal_id,
        is_cached=False,
    )
