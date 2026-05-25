from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_approval_packet_by_version,
    get_ui_skill_version_record,
)


@dataclass(frozen=True)
class AgentCandidatePromotionReadinessResult:
    version_id: str
    skill_id: str
    version_status: str
    readiness_score: int
    evidence_attached: bool
    approval_packet_exists: bool
    ready_for_human_review: bool
    blocking_items: list[str] = field(default_factory=list)
    advisory_items: list[str] = field(default_factory=list)
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def check_candidate_promotion_readiness(
    version_id: str, session
) -> AgentCandidatePromotionReadinessResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidatePromotionReadinessResult(
            version_id=version_id,
            skill_id="",
            version_status="not_found",
            readiness_score=0,
            evidence_attached=False,
            approval_packet_exists=False,
            ready_for_human_review=False,
            blocking_items=["Candidate version not found"],
            blocking_reason="version_not_found",
        )

    promotion_readiness = json.loads(version_row.promotion_readiness_json or "{}")
    evidence_attached = promotion_readiness.get("source") == "agent_handoff_packet"
    readiness_score = promotion_readiness.get("readiness_score", 0)

    approval_pkt = get_agent_candidate_approval_packet_by_version(session, version_id)

    blocking_items: list[str] = []
    advisory_items: list[str] = []

    if version_row.status != "candidate":
        blocking_items.append(
            f"Version status is '{version_row.status}' — expected 'candidate'"
        )
    if not evidence_attached:
        blocking_items.append("Evidence not attached — call attach-evidence first")
    if readiness_score < 75:
        blocking_items.append(
            f"Readiness score {readiness_score}/100 below threshold (75)"
        )

    advisory_items.append("Human approval required before promotion to 'approved'")
    advisory_items.append("Activation requires a separate human decision after approval")
    advisory_items.append("This system prepares the request only — it does not approve")

    ready = len(blocking_items) == 0

    return AgentCandidatePromotionReadinessResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        version_status=version_row.status,
        readiness_score=readiness_score,
        evidence_attached=evidence_attached,
        approval_packet_exists=approval_pkt is not None,
        ready_for_human_review=ready,
        blocking_items=blocking_items,
        advisory_items=advisory_items,
    )
