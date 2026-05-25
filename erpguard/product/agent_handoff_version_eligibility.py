from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class HandoffVersionEligibilityIssue:
    code: str
    message: str


@dataclass(frozen=True)
class HandoffVersionEligibilityResult:
    packet_id: str
    eligible: bool
    candidate_exists: bool
    packet_status: str
    readiness_score: int
    issues: list[HandoffVersionEligibilityIssue] = field(default_factory=list)
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def check_handoff_version_eligibility(packet_id: str, session) -> HandoffVersionEligibilityResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffVersionEligibilityResult(
            packet_id=packet_id,
            eligible=False,
            candidate_exists=False,
            packet_status="not_found",
            readiness_score=0,
            issues=[HandoffVersionEligibilityIssue(code="packet_not_found", message="Handoff packet not found.")],
        )

    packet_data = json.loads(packet.packet_json or "{}")
    readiness_score = packet_data.get("readiness_score", 0)

    existing_link = get_agent_handoff_version_link_by_packet(session, packet_id)
    if existing_link is not None:
        return HandoffVersionEligibilityResult(
            packet_id=packet_id,
            eligible=False,
            candidate_exists=True,
            packet_status=packet.status,
            readiness_score=readiness_score,
            issues=[HandoffVersionEligibilityIssue(
                code="candidate_already_exists",
                message=f"Candidate version already created: {existing_link.version_id}",
            )],
        )

    issues: list[HandoffVersionEligibilityIssue] = []

    if packet.status not in ("pending_human_review",):
        issues.append(HandoffVersionEligibilityIssue(
            code="invalid_packet_status",
            message=f"Packet status '{packet.status}' is not eligible. Expected 'pending_human_review'.",
        ))

    sec_safety = next(
        (s for s in packet_data.get("sections", []) if s.get("section_id") == "sec_safety"),
        None,
    )
    if sec_safety:
        safety = sec_safety.get("content", {})
        if safety.get("can_execute") is True:
            issues.append(HandoffVersionEligibilityIssue(
                code="can_execute_true",
                message="Packet has can_execute=True — cannot create candidate from executable draft.",
            ))
        if not safety.get("is_advisory_only", True):
            issues.append(HandoffVersionEligibilityIssue(
                code="not_advisory_only",
                message="Draft is not advisory-only — ineligible for governed handoff.",
            ))

    return HandoffVersionEligibilityResult(
        packet_id=packet_id,
        eligible=len(issues) == 0,
        candidate_exists=False,
        packet_status=packet.status,
        readiness_score=readiness_score,
        issues=issues,
    )
