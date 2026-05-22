from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.operator_evidence import (
    AssembleEvidencePackRequest,
    DemoSeedRequest,
    DemoSeedResponse,
    EvidencePackResponse,
    FinalReportResponse,
    RunbookResponse,
    SafetyReportResponse,
)
from erpguard.product.operator_demo_seed import OperatorDemoSeedService
from erpguard.product.operator_evidence_pack import OperatorEvidencePackService
from erpguard.product.operator_safety_report import OperatorSafetyReportService
from erpguard.product.operator_runbook_summary import OperatorRunbookSummaryService
from erpguard.product.operator_demo_report import OperatorDemoReportService


router = APIRouter(prefix="/v1/operator", tags=["operator-evidence"])

_seed_svc = OperatorDemoSeedService()
_pack_svc = OperatorEvidencePackService()
_safety_svc = OperatorSafetyReportService()
_runbook_svc = OperatorRunbookSummaryService()
_report_svc = OperatorDemoReportService()


@router.post("/demo-seed", response_model=DemoSeedResponse)
def operator_demo_seed(request: DemoSeedRequest | None = None):
    operator = (request.operator if request else None) or "demo_operator"
    try:
        result = _seed_svc.seed(operator=operator)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "demo_seed_error", "detail": str(exc)}},
        )
    return DemoSeedResponse(
        session_id=result.session_id,
        draft_id=result.draft_id,
        skill_id=result.skill_id,
        compiled_skill_id=result.compiled_skill_id,
        version_id=result.version_id,
        run_id=result.run_id,
        schedule_id=result.schedule_id,
        scenario_label=result.scenario_label,
        erp_target=result.erp_target,
        safety_invariants=result.safety_invariants,
        notes=result.notes,
    )


@router.post("/evidence-packs", response_model=EvidencePackResponse)
def assemble_evidence_pack(request: AssembleEvidencePackRequest | None = None):
    created_by = (request.created_by if request else None) or "manual_operator"
    scenario_label = (request.scenario_label if request else None) or "Fake ERP Formula Review — End-to-End Demo"
    seed_result = (request.seed_result if request else None) or {}
    try:
        result = _pack_svc.assemble(
            seed_result=seed_result,
            created_by=created_by,
            scenario_label=scenario_label,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "evidence_pack_error", "detail": str(exc)}},
        )
    return EvidencePackResponse(
        pack_id=result.pack_id,
        created_by=result.created_by,
        scenario_label=result.scenario_label,
        sprint_chain=result.sprint_chain,
        evidence_status=result.evidence_status,
        seed_result=result.seed_result,
        safety_checks=result.safety_checks,
        runbook_summary=result.runbook_summary,
        test_evidence=result.test_evidence,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/evidence-packs/{pack_id}", response_model=EvidencePackResponse)
def get_evidence_pack(pack_id: str):
    result = _pack_svc.get(pack_id)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "evidence_pack_not_found", "pack_id": pack_id}},
        )
    return EvidencePackResponse(
        pack_id=result.pack_id,
        created_by=result.created_by,
        scenario_label=result.scenario_label,
        sprint_chain=result.sprint_chain,
        evidence_status=result.evidence_status,
        seed_result=result.seed_result,
        safety_checks=result.safety_checks,
        runbook_summary=result.runbook_summary,
        test_evidence=result.test_evidence,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/evidence-packs/{pack_id}/safety-report", response_model=SafetyReportResponse)
def get_pack_safety_report(pack_id: str):
    pack = _pack_svc.get(pack_id)
    if pack is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "evidence_pack_not_found", "pack_id": pack_id}},
        )
    safety = _safety_svc.generate()
    return SafetyReportResponse(
        generated_at=safety.generated_at,
        product=safety.product,
        sprint_chain=safety.sprint_chain,
        invariants_enforced=safety.invariants_enforced,
        invariants_violated=safety.invariants_violated,
        blocked_operations_count=safety.blocked_operations_count,
        invariants=safety.invariants,
        blocked_operations=safety.blocked_operations,
        sprint_coverage=safety.sprint_coverage,
        verdict=safety.verdict,
        verdict_detail=safety.verdict_detail,
    )


@router.get("/evidence-packs/{pack_id}/final-report", response_model=FinalReportResponse)
def get_pack_final_report(pack_id: str):
    pack = _pack_svc.get(pack_id)
    if pack is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "evidence_pack_not_found", "pack_id": pack_id}},
        )
    report = _report_svc.generate(seed_result=pack.seed_result, pack_id=pack_id)
    return FinalReportResponse(
        generated_at=report.generated_at,
        product=report.product,
        version=report.version,
        sprint_chain=report.sprint_chain,
        scenario_label=report.scenario_label,
        seed_result=report.seed_result,
        safety_verdict=report.safety_verdict,
        safety_detail=report.safety_detail,
        invariants_enforced=report.invariants_enforced,
        invariants_violated=report.invariants_violated,
        blocked_operations_count=report.blocked_operations_count,
        operation_count=report.operation_count,
        sprint_coverage=report.sprint_coverage,
        safety_invariants=report.safety_invariants,
        blocked_operations=report.blocked_operations,
        runbook_operations=report.runbook_operations,
        kill_switches=report.kill_switches,
        safety_flags=report.safety_flags,
        notes=report.notes,
    )


@router.get("/demo-runbook", response_model=RunbookResponse)
def get_demo_runbook():
    runbook = _runbook_svc.generate()
    return RunbookResponse(
        generated_at=runbook.generated_at,
        product=runbook.product,
        operation_count=runbook.operation_count,
        sprint_chain=runbook.sprint_chain,
        operations=runbook.operations,
        kill_switches=runbook.kill_switches,
        safety_flags=runbook.safety_flags,
    )
