from __future__ import annotations

import json

from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_advisory_proposal,
    get_advisory_proposal,
    get_advisory_session,
    list_advisory_proposals_for_session,
    update_advisory_proposal,
    update_advisory_session,
)
from erpguard.product.agent_clarification_questions import generate_questions
from erpguard.product.agent_guard_proposal import propose_guards
from erpguard.product.agent_intent_analyzer import analyze_intent
from erpguard.product.agent_mapping_suggester import suggest_mappings
from erpguard.product.agent_process_classifier import classify_process
from erpguard.product.agent_risk_summary import summarize_risk
from erpguard.product.agent_workflow_proposal import propose_workflow

_ADVISORY_SAFETY_NOTE = (
    "This proposal is non-executable. "
    "It must be reviewed, approved, and compiled before any automation can run."
)

_SAFETY_INVARIANTS = [
    "Advisory mode: no ERP writes",
    "Advisory mode: no browser automation",
    "Advisory mode: no MCP tool execution",
    "Advisory mode: no skill activation",
    "Advisory mode: no R3/R4 operations",
]


class ProposalStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def generate(self, session_id: str, request_text: str) -> dict:
        session_row = get_advisory_session(self.session, session_id)
        if session_row is None:
            raise ObjectNotFoundError(f"AdvisorySession '{session_id}' not found.")

        intent = analyze_intent(request_text)
        process = classify_process(intent.action_type, intent.target_entity)
        mappings = suggest_mappings(intent.target_entity)
        workflow = propose_workflow(intent.action_type, intent.target_entity, intent.trigger_type)
        guards = propose_guards(intent.action_type)
        has_write_steps = any(not s.is_read_only for s in workflow.steps)
        risk = summarize_risk(intent.action_type, intent.target_entity, has_write_steps)
        questions = generate_questions(
            intent.action_type, intent.target_entity, intent.trigger_type, intent.confidence
        )

        proposal_row = create_advisory_proposal(
            self.session,
            session_id=session_id,
            request_text=request_text,
            intent_json=json.dumps(intent.model_dump(), default=str),
            process_category=process.process_category,
            entity_mappings_json=json.dumps(
                [m.model_dump() for m in mappings.suggested_fields], default=str
            ),
            workflow_json=json.dumps(workflow.model_dump(), default=str),
            guards_json=json.dumps(guards.model_dump(), default=str),
            risk_summary_json=json.dumps(risk.model_dump(), default=str),
            clarification_questions_json=json.dumps(
                [q.model_dump() for q in questions], default=str
            ),
            revision_number=1,
            status="draft",
        )

        update_advisory_session(
            self.session,
            session_id,
            request_text=request_text,
            latest_proposal_id=proposal_row.id,
            status="proposal_generated",
        )

        return self._proposal_dict(proposal_row, process.process_description)

    def get(self, proposal_id: str) -> dict:
        row = get_advisory_proposal(self.session, proposal_id)
        if row is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")
        return self._proposal_dict(row)

    def revise(self, proposal_id: str, updated_request: str) -> dict:
        row = get_advisory_proposal(self.session, proposal_id)
        if row is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")

        intent = analyze_intent(updated_request)
        process = classify_process(intent.action_type, intent.target_entity)
        mappings = suggest_mappings(intent.target_entity)
        workflow = propose_workflow(intent.action_type, intent.target_entity, intent.trigger_type)
        guards = propose_guards(intent.action_type)
        has_write_steps = any(not s.is_read_only for s in workflow.steps)
        risk = summarize_risk(intent.action_type, intent.target_entity, has_write_steps)
        questions = generate_questions(
            intent.action_type, intent.target_entity, intent.trigger_type, intent.confidence
        )

        updated_row = update_advisory_proposal(
            self.session,
            proposal_id=proposal_id,
            request_text=updated_request,
            intent_json=json.dumps(intent.model_dump(), default=str),
            process_category=process.process_category,
            entity_mappings_json=json.dumps(
                [m.model_dump() for m in mappings.suggested_fields], default=str
            ),
            workflow_json=json.dumps(workflow.model_dump(), default=str),
            guards_json=json.dumps(guards.model_dump(), default=str),
            risk_summary_json=json.dumps(risk.model_dump(), default=str),
            clarification_questions_json=json.dumps(
                [q.model_dump() for q in questions], default=str
            ),
            revision_number=row.revision_number + 1,
            status="revised",
        )

        session_row = get_advisory_session(self.session, row.session_id)
        if session_row is not None:
            update_advisory_session(
                self.session,
                row.session_id,
                request_text=updated_request,
                status="revised",
            )

        return self._proposal_dict(updated_row, process.process_description)

    def safety_summary(self, proposal_id: str) -> dict:
        row = get_advisory_proposal(self.session, proposal_id)
        if row is None:
            raise ObjectNotFoundError(f"AdvisoryProposal '{proposal_id}' not found.")
        return {
            "proposal_id": proposal_id,
            "is_advisory_only": True,
            "can_execute": False,
            "risk_summary": json.loads(row.risk_summary_json or "{}"),
            "guard_summary": json.loads(row.guards_json or "{}"),
            "safety_invariants": _SAFETY_INVARIANTS,
        }

    def _proposal_dict(self, row, process_description: str = "") -> dict:
        return {
            "proposal_id": row.id,
            "session_id": row.session_id,
            "request_text": row.request_text,
            "intent": json.loads(row.intent_json or "{}"),
            "process_category": row.process_category,
            "process_description": process_description,
            "entity_mappings": json.loads(row.entity_mappings_json or "[]"),
            "workflow": json.loads(row.workflow_json or "{}"),
            "guards": json.loads(row.guards_json or "{}"),
            "risk_summary": json.loads(row.risk_summary_json or "{}"),
            "clarification_questions": json.loads(row.clarification_questions_json or "[]"),
            "revision_number": row.revision_number,
            "status": row.status,
            "is_advisory_only": True,
            "can_execute": False,
            "safety_note": _ADVISORY_SAFETY_NOTE,
            "created_at": row.created_at.isoformat(),
        }
