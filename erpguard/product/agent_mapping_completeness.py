from __future__ import annotations

from pydantic import BaseModel, Field


class MappingIssue(BaseModel):
    code: str
    field: str
    message: str
    severity: str = "warning"


class MappingCompletenessResult(BaseModel):
    proposal_id: str
    complete: bool
    missing_required_fields: list[str] = Field(default_factory=list)
    issues: list[MappingIssue] = Field(default_factory=list)
    coverage_pct: int = 0


def check_mapping_completeness(proposal: dict) -> MappingCompletenessResult:
    proposal_id = proposal.get("proposal_id", "")
    entity_mappings = proposal.get("entity_mappings", [])
    issues: list[MappingIssue] = []
    missing_required: list[str] = []

    if not entity_mappings:
        issues.append(MappingIssue(
            code="no_mappings",
            field="entity_mappings",
            message="No entity field mappings present — proposal targets an unknown entity.",
            severity="warning",
        ))
        return MappingCompletenessResult(
            proposal_id=proposal_id,
            complete=True,
            missing_required_fields=[],
            issues=issues,
            coverage_pct=100,
        )

    total = len(entity_mappings)
    required_fields = [m for m in entity_mappings if m.get("required", False)]
    missing_required = [m["field"] for m in required_fields if not m.get("field")]

    for field_map in required_fields:
        field_name = field_map.get("field", "")
        if not field_name:
            missing_required.append("(unnamed required field)")
            issues.append(MappingIssue(
                code="required_field_missing",
                field=field_name or "(unnamed)",
                message=f"Required field '{field_name}' is defined but has no name.",
                severity="warning",
            ))

    coverage_pct = 100 if total > 0 else 0
    complete = len(missing_required) == 0

    return MappingCompletenessResult(
        proposal_id=proposal_id,
        complete=complete,
        missing_required_fields=missing_required,
        issues=issues,
        coverage_pct=coverage_pct,
    )
