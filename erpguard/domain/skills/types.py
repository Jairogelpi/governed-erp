"""Compiled skill package shapes (master spec section 18.2).

Package sections are stored as one JSON document (`package_json` on
`SkillPackage`), not one row/file per section -- this codebase's existing
convention for compound artifacts (see `ProcessCandidate.candidate_definition_json`,
`ProcessReplayCase.decision_trace_json`).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CheckStatus = Literal["passed", "failed", "not_checked"]


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowStep(SkillModel):
    step_name: str
    capability: str


class CapabilityManifestEntry(SkillModel):
    capability: str
    connector_id: str
    version: str
    safety_tier: str
    supports_execution: bool


class CheckResult(SkillModel):
    name: str
    status: CheckStatus
    detail: str = ""


class CompilationValidationResult(SkillModel):
    """Which of spec 18.3's checks this compiler can genuinely run, and
    which are structural placeholders -- see `compiler.py` module docstring
    for exactly what each `not_checked` item means and why.
    """

    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def all_real_checks_passed(self) -> bool:
        return all(item.status != "failed" for item in self.checks)


class SkillPackageContent(SkillModel):
    skill_yaml: dict[str, Any]
    process_ref_yaml: dict[str, Any]
    workflow_yaml: list[WorkflowStep]
    capability_manifest: list[CapabilityManifestEntry]
    policy_bundle: list[dict[str, Any]]
    guards: list[str]
    invariants: list[str]
    permissions: dict[str, Any]
    fingerprint_requirements: dict[str, Any]
    postconditions: list[dict[str, Any]]
    compensation: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    proof_of_improvement_ref: dict[str, Any]
    audit_config: dict[str, Any]
