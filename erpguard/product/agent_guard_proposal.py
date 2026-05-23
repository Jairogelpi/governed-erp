from __future__ import annotations

from pydantic import BaseModel, Field


_MANDATORY_GUARDS = [
    "no_generic_writes",
    "no_r3_r4_writes",
    "no_raw_tool_execution",
    "requires_human_review",
]

_ACTION_GUARDS: dict[str, list[str]] = {
    "validate": ["formula_guard", "odoo_readonly_guard"],
    "read": ["odoo_readonly_guard"],
    "report": ["odoo_readonly_guard"],
    "confirm": ["formula_guard", "write_readiness_required", "approval_required", "snapshot_required", "rollback_required"],
    "update": ["write_readiness_required", "approval_required", "snapshot_required", "rollback_required"],
    "create": ["write_readiness_required", "approval_required", "idempotency_required"],
    "send": ["approval_required"],
    "delete": ["write_readiness_required", "approval_required", "snapshot_required", "rollback_required"],
}

_GUARD_CATALOG: dict[str, dict] = {
    "no_generic_writes": {
        "label": "No Generic Writes",
        "description": "Prevents free-form ERP write operations without explicit certification",
        "mandatory": True,
        "category": "safety",
    },
    "no_r3_r4_writes": {
        "label": "No R3/R4 Writes",
        "description": "Blocks high-risk and destructive write categories",
        "mandatory": True,
        "category": "safety",
    },
    "no_raw_tool_execution": {
        "label": "No Raw Tool Execution",
        "description": "Prevents direct tool/MCP execution without a deterministic wrapper",
        "mandatory": True,
        "category": "safety",
    },
    "requires_human_review": {
        "label": "Requires Human Review",
        "description": "All automation proposals require human review before deployment",
        "mandatory": True,
        "category": "governance",
    },
    "formula_guard": {
        "label": "Formula Guard",
        "description": "Validates ERP formulas and business rules before execution",
        "mandatory": False,
        "category": "business_rule",
    },
    "odoo_readonly_guard": {
        "label": "Odoo Read-Only Guard",
        "description": "Restricts all ERP operations to read-only mode",
        "mandatory": False,
        "category": "safety",
    },
    "write_readiness_required": {
        "label": "Write Readiness Required",
        "description": "Skill must pass Write Readiness Assessment before any write can execute",
        "mandatory": False,
        "category": "governance",
    },
    "approval_required": {
        "label": "Approval Required",
        "description": "Human approval required for any state-changing operation",
        "mandatory": False,
        "category": "governance",
    },
    "idempotency_required": {
        "label": "Idempotency Required",
        "description": "Write operations must be idempotent to prevent duplicates",
        "mandatory": False,
        "category": "safety",
    },
    "snapshot_required": {
        "label": "Snapshot Required",
        "description": "Before-state snapshot required for audit and rollback",
        "mandatory": False,
        "category": "audit",
    },
    "rollback_required": {
        "label": "Rollback Required",
        "description": "Rollback plan required before executing any irreversible write",
        "mandatory": False,
        "category": "safety",
    },
}


class GuardDefinition(BaseModel):
    guard_id: str
    label: str
    description: str
    mandatory: bool = False
    category: str = "safety"


class GuardProposal(BaseModel):
    mandatory_guards: list[GuardDefinition] = Field(default_factory=list)
    recommended_guards: list[GuardDefinition] = Field(default_factory=list)
    all_guard_ids: list[str] = Field(default_factory=list)
    advisory_note: str = (
        "These guards are advisory recommendations. "
        "Final guard selection must be validated before skill compilation."
    )


def propose_guards(action_type: str) -> GuardProposal:
    mandatory = [GuardDefinition(guard_id=g, **_GUARD_CATALOG[g]) for g in _MANDATORY_GUARDS]
    recommended_ids = _ACTION_GUARDS.get(action_type, [])
    recommended = [
        GuardDefinition(guard_id=g, **_GUARD_CATALOG[g])
        for g in recommended_ids
        if g in _GUARD_CATALOG
    ]
    return GuardProposal(
        mandatory_guards=mandatory,
        recommended_guards=recommended,
        all_guard_ids=_MANDATORY_GUARDS + recommended_ids,
    )
