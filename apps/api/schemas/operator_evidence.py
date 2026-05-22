from __future__ import annotations

from pydantic import BaseModel, Field


class DemoSeedRequest(BaseModel):
    operator: str = "demo_operator"


class DemoSeedResponse(BaseModel):
    session_id: str
    draft_id: str
    skill_id: str
    compiled_skill_id: str
    version_id: str
    run_id: str
    schedule_id: str
    scenario_label: str
    erp_target: str
    safety_invariants: list[str]
    notes: list[str]


class AssembleEvidencePackRequest(BaseModel):
    created_by: str = "manual_operator"
    scenario_label: str = "Fake ERP Formula Review — End-to-End Demo"
    seed_result: dict = Field(default_factory=dict)


class EvidencePackResponse(BaseModel):
    pack_id: str
    created_by: str
    scenario_label: str
    sprint_chain: str
    evidence_status: str
    seed_result: dict
    safety_checks: dict
    runbook_summary: dict
    test_evidence: dict
    created_at: str
    updated_at: str


class SafetyReportResponse(BaseModel):
    generated_at: str
    product: str
    sprint_chain: str
    invariants_enforced: int
    invariants_violated: int
    blocked_operations_count: int
    invariants: list[dict]
    blocked_operations: list[str]
    sprint_coverage: list[dict]
    verdict: str
    verdict_detail: str


class FinalReportResponse(BaseModel):
    generated_at: str
    product: str
    version: str
    sprint_chain: str
    scenario_label: str
    seed_result: dict
    safety_verdict: str
    safety_detail: str
    invariants_enforced: int
    invariants_violated: int
    blocked_operations_count: int
    operation_count: int
    sprint_coverage: list[dict]
    safety_invariants: list[dict]
    blocked_operations: list[str]
    runbook_operations: list[dict]
    kill_switches: list[str]
    safety_flags: list[dict]
    notes: list[str]


class RunbookResponse(BaseModel):
    generated_at: str
    product: str
    operation_count: int
    sprint_chain: str
    operations: list[dict]
    kill_switches: list[str]
    safety_flags: list[dict]
