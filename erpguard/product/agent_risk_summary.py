from __future__ import annotations

from pydantic import BaseModel, Field


_RISK_BY_ACTION: dict[str, dict] = {
    "read":     {"level": "low",     "reversible": True,  "requires_write_pilot": False, "requires_approval": False},
    "report":   {"level": "low",     "reversible": True,  "requires_write_pilot": False, "requires_approval": False},
    "validate": {"level": "low",     "reversible": True,  "requires_write_pilot": False, "requires_approval": False},
    "send":     {"level": "medium",  "reversible": False, "requires_write_pilot": False, "requires_approval": True},
    "create":   {"level": "medium",  "reversible": False, "requires_write_pilot": True,  "requires_approval": True},
    "update":   {"level": "medium",  "reversible": True,  "requires_write_pilot": True,  "requires_approval": True},
    "confirm":  {"level": "high",    "reversible": False, "requires_write_pilot": True,  "requires_approval": True},
    "delete":   {"level": "high",    "reversible": False, "requires_write_pilot": True,  "requires_approval": True},
    "unknown":  {"level": "unknown", "reversible": None,  "requires_write_pilot": False, "requires_approval": True},
}

_HIGH_RISK_ENTITIES = {"invoice", "payment"}


class RiskSummary(BaseModel):
    overall_risk_level: str = "unknown"
    reversible: bool | None = None
    requires_write_pilot: bool = False
    requires_approval: bool = True
    risk_factors: list[str] = Field(default_factory=list)
    safe_for_advisory_only: bool = True
    can_execute_in_advisory_mode: bool = False
    advisory_note: str = (
        "This risk summary is advisory only. "
        "Actual risk depends on your Odoo configuration and data."
    )


def summarize_risk(action_type: str, target_entity: str, has_write_steps: bool = False) -> RiskSummary:
    config = _RISK_BY_ACTION.get(action_type, _RISK_BY_ACTION["unknown"])

    risk_factors: list[str] = []
    if config["reversible"] is False:
        risk_factors.append("Operation is not reversible once executed")
    if config["requires_write_pilot"]:
        risk_factors.append("Requires Write Pilot certification before execution")
    if config["requires_approval"]:
        risk_factors.append("Human approval required")
    if has_write_steps:
        risk_factors.append("Workflow contains write steps")
    if action_type in ("confirm", "delete"):
        risk_factors.append("High-impact state change on ERP records")
    if target_entity in _HIGH_RISK_ENTITIES:
        risk_factors.append(f"Financial record ({target_entity}) — extra care required")

    return RiskSummary(
        overall_risk_level=config["level"],
        reversible=config["reversible"],
        requires_write_pilot=config["requires_write_pilot"],
        requires_approval=config["requires_approval"],
        risk_factors=risk_factors,
        safe_for_advisory_only=True,
        can_execute_in_advisory_mode=False,
    )
