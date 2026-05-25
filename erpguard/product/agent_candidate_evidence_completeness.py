from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record

_REQUIRED_EVIDENCE_SOURCES = [
    "bridge_review",
    "bridge_validation",
    "bridge_compile_plan",
    "readiness_score",
    "safety_invariants",
]


@dataclass(frozen=True)
class EvidenceItem:
    source: str
    status: str
    label: str
    complete: bool


@dataclass(frozen=True)
class AgentCandidateEvidenceCompletenessResult:
    version_id: str
    skill_id: str
    evidence_attached: bool
    complete: bool
    items_found: int
    items_required: int
    items: list[EvidenceItem] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def check_evidence_completeness(
    version_id: str, session
) -> AgentCandidateEvidenceCompletenessResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateEvidenceCompletenessResult(
            version_id=version_id,
            skill_id="",
            evidence_attached=False,
            complete=False,
            items_found=0,
            items_required=len(_REQUIRED_EVIDENCE_SOURCES),
            blocking_reason="version_not_found",
        )

    promotion_readiness = json.loads(version_row.promotion_readiness_json or "{}")
    raw_items: list[dict] = promotion_readiness.get("evidence_items", [])

    found_sources = {item["source"] for item in raw_items}
    missing = [s for s in _REQUIRED_EVIDENCE_SOURCES if s not in found_sources]

    items = [
        EvidenceItem(
            source=item["source"],
            status=item.get("status", "unknown"),
            label=item.get("label", item["source"]),
            complete=item.get("status") not in ("unknown", "failed", "not_run"),
        )
        for item in raw_items
    ]

    evidence_attached = promotion_readiness.get("source") == "agent_handoff_packet"
    complete = evidence_attached and len(missing) == 0

    return AgentCandidateEvidenceCompletenessResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        evidence_attached=evidence_attached,
        complete=complete,
        items_found=len(items),
        items_required=len(_REQUIRED_EVIDENCE_SOURCES),
        items=items,
        missing_sources=missing,
    )
