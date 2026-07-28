from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_draft_handoff_packet_by_id,
    get_agent_handoff_version_link_by_packet,
    list_agent_handoff_version_events_for_packet,
)


@dataclass(frozen=True)
class HandoffVersionAuditEntry:
    event_id: str
    packet_id: str
    step: str
    status: str
    detail: dict
    created_at: str


@dataclass(frozen=True)
class HandoffVersionAuditResult:
    packet_id: str
    version_id: str | None
    event_count: int
    events: list[HandoffVersionAuditEntry] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_version_audit(packet_id: str, session) -> HandoffVersionAuditResult:
    packet = get_agent_draft_handoff_packet_by_id(session, packet_id)
    if packet is None:
        return HandoffVersionAuditResult(
            packet_id=packet_id, version_id=None,
            event_count=0, events=[],
        )

    link = get_agent_handoff_version_link_by_packet(session, packet_id)
    rows = list_agent_handoff_version_events_for_packet(session, packet_id)

    entries = [
        HandoffVersionAuditEntry(
            event_id=r.id,
            packet_id=r.packet_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json) if r.detail_json else {},
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    return HandoffVersionAuditResult(
        packet_id=packet_id,
        version_id=link.version_id if link else None,
        event_count=len(entries),
        events=entries,
    )
