from __future__ import annotations

import json

from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_agent_proposal_draft_link,
    create_automation_draft,
    get_advisory_proposal,
    get_agent_proposal_draft_link_by_draft,
    get_agent_proposal_draft_link_by_proposal,
    get_automation_draft,
    update_advisory_proposal,
)
from erpguard.product.agent_draft_preview import DraftPreview, preview_draft
from erpguard.product.agent_draft_safety_policy import enforce_draft_safety
from erpguard.product.agent_mapping_completeness import check_mapping_completeness
from erpguard.product.agent_proposal_eligibility import check_eligibility
from erpguard.product.agent_proposal_to_draft import transform_proposal_to_draft


class AgentDraftService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── preview (non-persisted) ──────────────────────────────────────────────

    def preview(self, proposal_id: str) -> DraftPreview:
        proposal = self._load_proposal_dict(proposal_id)
        return preview_draft(proposal)

    # ── create draft (persisted) ─────────────────────────────────────────────

    def create_draft(self, proposal_id: str) -> dict:
        proposal_row = get_advisory_proposal(self.session, proposal_id)
        if proposal_row is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")

        if get_agent_proposal_draft_link_by_proposal(self.session, proposal_id) is not None:
            raise ValueError(f"A draft already exists for proposal '{proposal_id}'.")

        proposal = self._row_to_dict(proposal_row)

        eligibility = check_eligibility(proposal)
        if not eligibility.eligible:
            codes = [i.code for i in eligibility.issues]
            raise ValueError(f"Proposal not eligible for draft creation: {codes}")

        transform = transform_proposal_to_draft(proposal)
        safety = enforce_draft_safety(transform, proposal)
        if not safety.passed:
            codes = [v.code for v in safety.violations]
            raise ValueError(f"Safety policy violations prevent draft creation: {codes}")

        draft_row = create_automation_draft(
            self.session,
            opportunity_id=transform.opportunity_id,
            scan_id=transform.scan_id,
            snapshot_id=transform.snapshot_id,
            connection_id=transform.connection_id,
            name=transform.name,
            description=transform.description,
            runtime_mode=transform.runtime_mode,
            write_actions=transform.write_actions,
            draft_json=transform.draft_json,
            status=transform.status,
        )

        link = create_agent_proposal_draft_link(
            self.session,
            proposal_id=proposal_id,
            draft_id=draft_row.id,
            session_id=proposal_row.session_id,
        )

        update_advisory_proposal(self.session, proposal_id, status="draft_created")

        return self._draft_response(draft_row, proposal_id, link.id)

    # ── draft-link ───────────────────────────────────────────────────────────

    def get_draft_link(self, proposal_id: str) -> dict:
        if get_advisory_proposal(self.session, proposal_id) is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")

        link = get_agent_proposal_draft_link_by_proposal(self.session, proposal_id)
        if link is None:
            return {
                "proposal_id": proposal_id,
                "draft_id": None,
                "link_id": None,
                "has_draft": False,
                "message": "No draft has been created for this proposal yet.",
            }
        return {
            "proposal_id": proposal_id,
            "draft_id": link.draft_id,
            "link_id": link.id,
            "has_draft": True,
            "created_at": link.created_at.isoformat(),
        }

    # ── source proposal (reverse lookup) ─────────────────────────────────────

    def get_source_proposal(self, draft_id: str) -> dict:
        if get_automation_draft(self.session, draft_id) is None:
            raise ObjectNotFoundError(f"AutomationDraft '{draft_id}' not found.")

        link = get_agent_proposal_draft_link_by_draft(self.session, draft_id)
        if link is None:
            raise ObjectNotFoundError(
                f"AutomationDraft '{draft_id}' was not created from an agent advisory proposal."
            )

        proposal_row = get_advisory_proposal(self.session, link.proposal_id)
        if proposal_row is None:
            raise ObjectNotFoundError(
                f"Source proposal '{link.proposal_id}' no longer exists."
            )

        return {
            "draft_id": draft_id,
            "proposal_id": link.proposal_id,
            "session_id": link.session_id,
            "link_id": link.id,
            "proposal": self._row_to_dict(proposal_row),
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _load_proposal_dict(self, proposal_id: str) -> dict:
        row = get_advisory_proposal(self.session, proposal_id)
        if row is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")
        return self._row_to_dict(row)

    def _row_to_dict(self, row) -> dict:
        return {
            "proposal_id": row.id,
            "session_id": row.session_id,
            "request_text": row.request_text,
            "intent": json.loads(row.intent_json or "{}"),
            "process_category": row.process_category,
            "process_description": "",
            "entity_mappings": json.loads(row.entity_mappings_json or "[]"),
            "workflow": json.loads(row.workflow_json or "{}"),
            "guards": json.loads(row.guards_json or "{}"),
            "risk_summary": json.loads(row.risk_summary_json or "{}"),
            "clarification_questions": json.loads(row.clarification_questions_json or "[]"),
            "revision_number": row.revision_number,
            "status": row.status,
            "is_advisory_only": True,
            "can_execute": False,
            "created_at": row.created_at.isoformat(),
        }

    def _draft_response(self, draft_row, proposal_id: str, link_id: str) -> dict:
        return {
            "draft_id": draft_row.id,
            "proposal_id": proposal_id,
            "link_id": link_id,
            "name": draft_row.name,
            "description": draft_row.description,
            "status": draft_row.status,
            "runtime_mode": draft_row.runtime_mode,
            "write_actions": draft_row.write_actions,
            "created_at": draft_row.created_at.isoformat(),
            "safety": {
                "runtime_mode": "dry_run_only",
                "write_actions": False,
                "requires_human_review": True,
                "requires_approval": True,
                "can_execute": False,
                "is_advisory_only": True,
            },
            "next_step": "human_review",
            "advisory_note": (
                "Draft created from advisory proposal. "
                "Requires human review, validation, compilation, and approval before any activation."
            ),
        }
