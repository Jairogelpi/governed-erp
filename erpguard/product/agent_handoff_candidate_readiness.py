from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
    get_ui_skill_version_record,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class HandoffCandidateReadinessResult:
    packet_id: str
    version_id: str
    version_status: str
    evidence_attached: bool
    readiness_score: int
    ready_for_promotion: bool
    blocking_items: list[str] = field(default_factory=list)
    advisory_items: list[str] = field(default_factory=list)
    can_approve: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def check_candidate_readiness(packet_id: str, session) -> HandoffCandidateReadinessResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffCandidateReadinessResult(
            packet_id=packet_id, version_id="",
            version_status="not_found", evidence_attached=False,
            readiness_score=0, ready_for_promotion=False,
            blocking_items=["Handoff packet not found"],
            blocking_reason="packet_not_found",
        )

    link = get_agent_handoff_version_link_by_packet(session, packet_id)
    if link is None:
        return HandoffCandidateReadinessResult(
            packet_id=packet_id, version_id="",
            version_status="not_created", evidence_attached=False,
            readiness_score=0, ready_for_promotion=False,
            blocking_items=["Candidate version not yet created — call create-candidate-version first"],
            blocking_reason="candidate_not_created",
        )

    version_row = get_ui_skill_version_record(session, link.version_id)
    if version_row is None:
        return HandoffCandidateReadinessResult(
            packet_id=packet_id, version_id=link.version_id,
            version_status="missing", evidence_attached=False,
            readiness_score=0, ready_for_promotion=False,
            blocking_items=["Version record not found in DB"],
            blocking_reason="version_record_missing",
        )

    packet_data = json.loads(packet.packet_json or "{}")
    readiness_score = packet_data.get("readiness_score", 0)

    promotion_readiness = json.loads(version_row.promotion_readiness_json or "{}")
    evidence_attached = bool(promotion_readiness.get("source") == "agent_handoff_packet")

    blocking_items: list[str] = []
    advisory_items: list[str] = []

    if version_row.status != "candidate":
        blocking_items.append(f"Version status is '{version_row.status}' — expected 'candidate'")

    if not evidence_attached:
        blocking_items.append("Evidence not attached — call attach-evidence first")

    if readiness_score < 75:
        blocking_items.append(f"Readiness score {readiness_score}/100 below threshold (75)")

    advisory_items.append("Human approval required before promotion to 'approved'")
    advisory_items.append("Activation requires separate human decision after approval")
    advisory_items.append("Draft remains dry_run_only until a human explicitly promotes")

    ready = len(blocking_items) == 0

    return HandoffCandidateReadinessResult(
        packet_id=packet_id,
        version_id=link.version_id,
        version_status=version_row.status,
        evidence_attached=evidence_attached,
        readiness_score=readiness_score,
        ready_for_promotion=ready,
        blocking_items=blocking_items,
        advisory_items=advisory_items,
    )
