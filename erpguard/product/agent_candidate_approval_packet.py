from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_candidate_approval_event,
    create_agent_candidate_approval_packet,
    get_agent_candidate_approval_packet_by_version,
    get_ui_skill_version_record,
)
from erpguard.product.agent_candidate_evidence_completeness import check_evidence_completeness
from erpguard.product.agent_candidate_risk_summary import get_risk_summary

_APPROVAL_INSTRUCTIONS = (
    "Human reviewer must evaluate this candidate skill version and decide "
    "whether to approve it for promotion. Approval must happen through the "
    "external change-management process. This system does not approve automatically."
)

_SAFETY_NOTE = (
    "can_execute=False | can_approve=False | is_advisory_only=True | "
    "requires_human_review=True | no_automatic_activation=True"
)


@dataclass(frozen=True)
class AgentCandidateApprovalPacketResult:
    version_id: str
    skill_id: str
    approval_packet_id: str
    status: str
    readiness_score: int
    evidence_complete: bool
    risk_level: str
    guard_names: list[str]
    approval_instructions: str
    safety_note: str
    is_cached: bool = False
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def create_approval_packet(
    version_id: str, session
) -> AgentCandidateApprovalPacketResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateApprovalPacketResult(
            version_id=version_id,
            skill_id="",
            approval_packet_id="",
            status="blocked",
            readiness_score=0,
            evidence_complete=False,
            risk_level="unknown",
            guard_names=[],
            approval_instructions=_APPROVAL_INSTRUCTIONS,
            safety_note=_SAFETY_NOTE,
            blocking_reason="version_not_found",
        )

    existing = get_agent_candidate_approval_packet_by_version(session, version_id)
    evidence = check_evidence_completeness(version_id, session)
    risk = get_risk_summary(version_id, session)

    import json as _json
    promotion_readiness = _json.loads(version_row.promotion_readiness_json or "{}")
    readiness_score = promotion_readiness.get("readiness_score", 0)

    if existing is not None:
        return AgentCandidateApprovalPacketResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            approval_packet_id=existing.id,
            status=existing.status,
            readiness_score=readiness_score,
            evidence_complete=evidence.complete,
            risk_level=risk.risk_level,
            guard_names=risk.guard_names,
            approval_instructions=_APPROVAL_INSTRUCTIONS,
            safety_note=_SAFETY_NOTE,
            is_cached=True,
        )

    packet_data = {
        "version_id": version_id,
        "skill_id": version_row.skill_id,
        "version_name": version_row.name,
        "version_status": version_row.status,
        "runtime_type": version_row.runtime_type,
        "readiness_score": readiness_score,
        "evidence_complete": evidence.complete,
        "evidence_items": [
            {"source": i.source, "status": i.status, "label": i.label}
            for i in evidence.items
        ],
        "risk_level": risk.risk_level,
        "risk_flags": risk.risk_flags,
        "guard_names": risk.guard_names,
        "safety_invariants": {
            "can_execute": False,
            "can_approve": False,
            "is_advisory_only": True,
            "requires_human_review": True,
            "no_automatic_activation": True,
        },
        "approval_instructions": _APPROVAL_INSTRUCTIONS,
        "safety_note": _SAFETY_NOTE,
    }

    pkt = create_agent_candidate_approval_packet(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        packet_json=json.dumps(packet_data),
    )

    create_agent_candidate_approval_event(
        session, version_id, "create_approval_packet", "completed",
        json.dumps({"approval_packet_id": pkt.id, "readiness_score": readiness_score}),
    )

    return AgentCandidateApprovalPacketResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        approval_packet_id=pkt.id,
        status=pkt.status,
        readiness_score=readiness_score,
        evidence_complete=evidence.complete,
        risk_level=risk.risk_level,
        guard_names=risk.guard_names,
        approval_instructions=_APPROVAL_INSTRUCTIONS,
        safety_note=_SAFETY_NOTE,
        is_cached=False,
    )
