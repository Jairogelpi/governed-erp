from __future__ import annotations

import json

from pydantic import BaseModel, Field


_DRAFT_RUNTIME_MODE = "dry_run_only"
_DRAFT_STATUS = "pending_review"
_ADVISORY_SENTINEL = "agent_advisory"


class DraftTransformResult(BaseModel):
    name: str
    description: str
    runtime_mode: str = _DRAFT_RUNTIME_MODE
    write_actions: bool = False
    status: str = _DRAFT_STATUS
    draft_json: str = "{}"
    opportunity_id: str = _ADVISORY_SENTINEL
    scan_id: str = _ADVISORY_SENTINEL
    snapshot_id: str = _ADVISORY_SENTINEL
    connection_id: str = _ADVISORY_SENTINEL
    safety_note: str = (
        "Draft created from advisory proposal. "
        "Requires human review, validation, compilation, and approval before any activation."
    )


def transform_proposal_to_draft(proposal: dict) -> DraftTransformResult:
    intent = proposal.get("intent", {})
    action_type = intent.get("action_type", "unknown")
    target_entity = intent.get("target_entity", "unknown")
    process_category = proposal.get("process_category", "general")
    request_text = proposal.get("request_text", "")

    name = _build_name(action_type, target_entity, process_category)
    description = _build_description(request_text, process_category, action_type, target_entity)

    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal.get("proposal_id", ""),
        "session_id": proposal.get("session_id", ""),
        "intent": intent,
        "process_category": process_category,
        "process_description": proposal.get("process_description", ""),
        "workflow": proposal.get("workflow", {}),
        "guards": proposal.get("guards", {}),
        "risk_summary": proposal.get("risk_summary", {}),
        "entity_mappings": proposal.get("entity_mappings", []),
        "clarification_questions": proposal.get("clarification_questions", []),
        # Top-level safety fields so DraftValidatorService can read them directly
        "write_actions": False,
        "runtime_mode": _DRAFT_RUNTIME_MODE,
        "safety": {
            "runtime_mode": _DRAFT_RUNTIME_MODE,
            "write_actions": False,
            "requires_human_review": True,
            "requires_approval": True,
            "can_execute": False,
            "is_advisory_only": True,
        },
    }

    return DraftTransformResult(
        name=name,
        description=description,
        runtime_mode=_DRAFT_RUNTIME_MODE,
        write_actions=False,
        status=_DRAFT_STATUS,
        draft_json=json.dumps(draft_content, default=str),
        opportunity_id=f"agent_proposal:{proposal.get('proposal_id', '')}",
        scan_id=_ADVISORY_SENTINEL,
        snapshot_id=_ADVISORY_SENTINEL,
        connection_id=_ADVISORY_SENTINEL,
    )


def _build_name(action_type: str, target_entity: str, process_category: str) -> str:
    if action_type != "unknown" and target_entity != "unknown":
        entity_label = target_entity.replace("_", " ").title()
        action_label = action_type.capitalize()
        return f"[Agent] {action_label} {entity_label}"
    if process_category not in ("general", "unknown"):
        return f"[Agent] {process_category.replace('_', ' ').title()} Automation"
    return "[Agent] Advisory Automation Draft"


def _build_description(
    request_text: str, process_category: str, action_type: str, target_entity: str
) -> str:
    category_label = process_category.replace("_", " ").title()
    summary = f"Agent-advisory draft for {category_label} automation."
    if request_text:
        truncated = request_text[:160].rstrip()
        if len(request_text) > 160:
            truncated += "…"
        summary += f" Request: \"{truncated}\""
    summary += " Pending human review, validation, compilation, and approval."
    return summary
