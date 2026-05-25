from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_handoff_version_event,
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
    get_ui_skill_version_record,
    update_ui_skill_version_status,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class HandoffEvidenceAttachmentResult:
    packet_id: str
    version_id: str
    evidence_attached: bool
    bridge_steps_passed: int
    bridge_steps_total: int
    proof_plan_generated: bool
    readiness_score: int
    evidence_items: list[dict] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def attach_evidence_to_candidate(packet_id: str, session) -> HandoffEvidenceAttachmentResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffEvidenceAttachmentResult(
            packet_id=packet_id, version_id="", evidence_attached=False,
            bridge_steps_passed=0, bridge_steps_total=3,
            proof_plan_generated=False, readiness_score=0,
            blocking_reason="packet_not_found",
        )

    link = get_agent_handoff_version_link_by_packet(session, packet_id)
    if link is None:
        return HandoffEvidenceAttachmentResult(
            packet_id=packet_id, version_id="", evidence_attached=False,
            bridge_steps_passed=0, bridge_steps_total=3,
            proof_plan_generated=False, readiness_score=0,
            blocking_reason="candidate_not_created",
        )

    packet_data = json.loads(packet.packet_json or "{}")
    sections = {s["section_id"]: s["content"] for s in packet_data.get("sections", [])}
    bridge_data = sections.get("sec_bridge", {})
    readiness_data = sections.get("sec_readiness", {})
    readiness_score = packet_data.get("readiness_score", readiness_data.get("overall_score", 0))

    bridge_steps = ["review", "validation", "compile_plan"]
    bridge_steps_passed = sum(
        1 for s in bridge_steps if bridge_data.get(s) == "passed"
    )

    evidence_items = [
        {"source": "bridge_review", "status": bridge_data.get("review", "unknown"),
         "label": "ERPGuard Review Bridge"},
        {"source": "bridge_validation", "status": bridge_data.get("validation", "unknown"),
         "label": "ERPGuard Validation Bridge"},
        {"source": "bridge_compile_plan", "status": bridge_data.get("compile_plan", "unknown"),
         "label": "Compile Plan (advisory)"},
        {"source": "readiness_score", "status": "measured",
         "label": f"Approval Readiness Score: {readiness_score}/100"},
        {"source": "safety_invariants", "status": "enforced",
         "label": "can_execute=False, is_advisory_only=True, requires_human_review=True"},
    ]

    proof_plan_generated = False
    for s in packet_data.get("sections", []):
        if s.get("section_id") == "sec_readiness":
            checklist = s.get("content", {}).get("checklist", [])
            for item in checklist:
                if item.get("check_id") == "chk_proof_plan" and item.get("passed"):
                    proof_plan_generated = True

    promotion_readiness = {
        "source": "agent_handoff_packet",
        "packet_id": packet_id,
        "bridge_steps_passed": bridge_steps_passed,
        "bridge_steps_total": 3,
        "proof_plan_generated": proof_plan_generated,
        "readiness_score": readiness_score,
        "evidence_items": evidence_items,
        "can_execute": False,
        "is_advisory_only": True,
    }

    version_row = get_ui_skill_version_record(session, link.version_id)
    if version_row is not None:
        update_ui_skill_version_status(
            session, link.version_id,
            status=version_row.status,
            is_active=False,
            promotion_readiness_json=json.dumps(promotion_readiness),
        )

    create_agent_handoff_version_event(
        session, packet_id, "attach_evidence", "completed",
        json.dumps({"version_id": link.version_id, "evidence_count": len(evidence_items)}),
    )

    return HandoffEvidenceAttachmentResult(
        packet_id=packet_id,
        version_id=link.version_id,
        evidence_attached=True,
        bridge_steps_passed=bridge_steps_passed,
        bridge_steps_total=3,
        proof_plan_generated=proof_plan_generated,
        readiness_score=readiness_score,
        evidence_items=evidence_items,
    )
