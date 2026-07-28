from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_candidate_approval_event,
    get_ui_skill_version_record,
)
from erpguard.product.agent_candidate_approval_packet import create_approval_packet
from erpguard.product.agent_candidate_evidence_completeness import check_evidence_completeness
from erpguard.product.agent_candidate_promotion_readiness import check_candidate_promotion_readiness


@dataclass(frozen=True)
class BridgeStep:
    step: str
    status: str
    detail: str


@dataclass(frozen=True)
class AgentCandidateApprovalBridgeResult:
    version_id: str
    skill_id: str
    bridge_complete: bool
    approval_packet_id: str
    steps: list[BridgeStep] = field(default_factory=list)
    steps_passed: int = 0
    steps_total: int = 0
    blocking_reason: str = ""
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def run_approval_bridge(version_id: str, session) -> AgentCandidateApprovalBridgeResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateApprovalBridgeResult(
            version_id=version_id,
            skill_id="",
            bridge_complete=False,
            approval_packet_id="",
            blocking_reason="version_not_found",
        )

    steps: list[BridgeStep] = []

    # Step 1: promotion readiness check
    readiness = check_candidate_promotion_readiness(version_id, session)
    step1_ok = readiness.ready_for_human_review
    steps.append(BridgeStep(
        step="promotion_readiness",
        status="passed" if step1_ok else "failed",
        detail=(
            f"readiness_score={readiness.readiness_score}, "
            f"evidence_attached={readiness.evidence_attached}"
        ),
    ))
    create_agent_candidate_approval_event(
        session, version_id, "promotion_readiness",
        "passed" if step1_ok else "failed",
        json.dumps({"readiness_score": readiness.readiness_score,
                    "blocking_items": readiness.blocking_items}),
    )

    # Step 2: evidence completeness check
    evidence = check_evidence_completeness(version_id, session)
    step2_ok = evidence.complete
    steps.append(BridgeStep(
        step="evidence_completeness",
        status="passed" if step2_ok else "advisory",
        detail=(
            f"items_found={evidence.items_found}/{evidence.items_required}, "
            f"missing={evidence.missing_sources}"
        ),
    ))
    create_agent_candidate_approval_event(
        session, version_id, "evidence_completeness",
        "passed" if step2_ok else "advisory",
        json.dumps({"items_found": evidence.items_found,
                    "missing_sources": evidence.missing_sources}),
    )

    # Step 3: create/retrieve approval packet
    pkt_result = create_approval_packet(version_id, session)
    step3_ok = bool(pkt_result.approval_packet_id)
    steps.append(BridgeStep(
        step="approval_packet",
        status="passed" if step3_ok else "failed",
        detail=f"approval_packet_id={pkt_result.approval_packet_id}",
    ))
    create_agent_candidate_approval_event(
        session, version_id, "approval_packet",
        "passed" if step3_ok else "failed",
        json.dumps({"approval_packet_id": pkt_result.approval_packet_id,
                    "is_cached": pkt_result.is_cached}),
    )

    steps_passed = sum(1 for s in steps if s.status == "passed")
    bridge_complete = step3_ok

    return AgentCandidateApprovalBridgeResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        bridge_complete=bridge_complete,
        approval_packet_id=pkt_result.approval_packet_id,
        steps=steps,
        steps_passed=steps_passed,
        steps_total=len(steps),
    )
