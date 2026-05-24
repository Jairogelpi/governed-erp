from __future__ import annotations

import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_clarification_audit_event,
    create_mapping_confirmation,
    get_advisory_proposal,
    get_latest_mapping_confirmation_for_key,
    list_mapping_confirmations_for_proposal,
)


class MappingConfirmationResult(BaseModel):
    proposal_id: str
    mapping_key: str
    action: str
    reason: str | None = None
    previous_action: str | None = None
    is_advisory_only: bool = True
    can_execute: bool = False


class MappingSummary(BaseModel):
    mapping_key: str
    action: str
    reason: str | None = None


class MappingConfirmationsView(BaseModel):
    proposal_id: str
    confirmations: list[MappingSummary]
    total: int
    confirmed_count: int
    rejected_count: int


def _valid_keys_for_proposal(proposal) -> set[str]:
    mappings = json.loads(proposal.entity_mappings_json or "[]")
    keys: set[str] = set()
    for i, m in enumerate(mappings):
        field = m.get("field", "")
        odoo_field = m.get("odoo_field", "")
        if field:
            keys.add(field)
        if odoo_field:
            keys.add(odoo_field)
        keys.add(str(i))
    return keys


def confirm_mapping(
    proposal_id: str,
    mapping_key: str,
    reason: str | None,
    session: Session,
) -> MappingConfirmationResult:
    proposal = get_advisory_proposal(session, proposal_id)
    previous = None
    if proposal is not None:
        prev_row = get_latest_mapping_confirmation_for_key(session, proposal_id, mapping_key)
        if prev_row:
            previous = prev_row.action

        create_mapping_confirmation(
            session,
            proposal_id=proposal_id,
            mapping_key=mapping_key,
            action="confirmed",
            reason=reason,
        )
        create_clarification_audit_event(
            session,
            proposal_id=proposal_id,
            event_type="mapping_confirmed",
            detail_json=json.dumps({"mapping_key": mapping_key, "reason": reason}),
        )

    return MappingConfirmationResult(
        proposal_id=proposal_id,
        mapping_key=mapping_key,
        action="confirmed",
        reason=reason,
        previous_action=previous,
        is_advisory_only=True,
        can_execute=False,
    )


def reject_mapping(
    proposal_id: str,
    mapping_key: str,
    reason: str | None,
    session: Session,
) -> MappingConfirmationResult:
    proposal = get_advisory_proposal(session, proposal_id)
    previous = None
    if proposal is not None:
        prev_row = get_latest_mapping_confirmation_for_key(session, proposal_id, mapping_key)
        if prev_row:
            previous = prev_row.action

        create_mapping_confirmation(
            session,
            proposal_id=proposal_id,
            mapping_key=mapping_key,
            action="rejected",
            reason=reason,
        )
        create_clarification_audit_event(
            session,
            proposal_id=proposal_id,
            event_type="mapping_rejected",
            detail_json=json.dumps({"mapping_key": mapping_key, "reason": reason}),
        )

    return MappingConfirmationResult(
        proposal_id=proposal_id,
        mapping_key=mapping_key,
        action="rejected",
        reason=reason,
        previous_action=previous,
        is_advisory_only=True,
        can_execute=False,
    )


def list_mapping_confirmations(
    proposal_id: str,
    session: Session,
) -> MappingConfirmationsView:
    rows = list_mapping_confirmations_for_proposal(session, proposal_id)
    seen: dict[str, MappingSummary] = {}
    for row in rows:
        seen[row.mapping_key] = MappingSummary(
            mapping_key=row.mapping_key,
            action=row.action,
            reason=row.reason,
        )
    summaries = list(seen.values())
    confirmed = sum(1 for s in summaries if s.action == "confirmed")
    rejected = sum(1 for s in summaries if s.action == "rejected")
    return MappingConfirmationsView(
        proposal_id=proposal_id,
        confirmations=summaries,
        total=len(summaries),
        confirmed_count=confirmed,
        rejected_count=rejected,
    )
