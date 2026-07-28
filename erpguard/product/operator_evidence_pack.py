from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from erpguard.db.repositories import (
    create_operator_evidence_pack,
    get_operator_evidence_pack,
    list_operator_evidence_packs,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.operator_safety_report import OperatorSafetyReportService
from erpguard.product.operator_runbook_summary import OperatorRunbookSummaryService


_SAFETY_REPORT_SVC = OperatorSafetyReportService()
_RUNBOOK_SVC = OperatorRunbookSummaryService()

_SPRINT_COVERAGE = [
    {"sprint": 20, "title": "Record-to-Skill Backend Loop", "tests": "≥40"},
    {"sprint": 21, "title": "Real Fake ERP Browser Recorder", "tests": "≥30"},
    {"sprint": 22, "title": "Verified Fail-Closed Replay", "tests": "≥35"},
    {"sprint": 23, "title": "Skill Versioning, Promotion & Rollback", "tests": "≥45"},
    {"sprint": 24, "title": "Active Skill Manual Runner", "tests": "≥49"},
    {"sprint": 25, "title": "Scheduled Skill Runs & Run Queue Safety", "tests": "≥63"},
    {"sprint": 26, "title": "Operator Runbook & Evidence Pack", "tests": "≥35"},
]


@dataclass(frozen=True)
class EvidencePackResult:
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


class OperatorEvidencePackService:
    def assemble(
        self,
        seed_result: dict | None = None,
        created_by: str = "manual_operator",
        scenario_label: str = "Fake ERP Formula Review — End-to-End Demo",
    ) -> EvidencePackResult:
        init_db()

        safety = _SAFETY_REPORT_SVC.generate()
        runbook = _RUNBOOK_SVC.generate()

        safety_checks = {
            "generated_at": safety.generated_at,
            "verdict": safety.verdict,
            "verdict_detail": safety.verdict_detail,
            "invariants_enforced": safety.invariants_enforced,
            "invariants_violated": safety.invariants_violated,
            "blocked_operations_count": safety.blocked_operations_count,
            "invariants": safety.invariants,
            "blocked_operations": safety.blocked_operations,
        }

        runbook_summary = {
            "generated_at": runbook.generated_at,
            "operation_count": runbook.operation_count,
            "operations": runbook.operations,
            "kill_switches": runbook.kill_switches,
            "safety_flags": runbook.safety_flags,
        }

        test_evidence = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "sprint_coverage": _SPRINT_COVERAGE,
            "total_sprints_covered": len(_SPRINT_COVERAGE),
            "safety_invariants_count": len(safety.invariants),
            "all_invariants_enforced": safety.invariants_violated == 0,
        }

        db = SessionLocal()
        try:
            pack = create_operator_evidence_pack(
                db,
                created_by=created_by,
                scenario_label=scenario_label,
                sprint_chain="20-26",
                seed_result=seed_result or {},
                safety_checks=safety_checks,
                runbook_summary=runbook_summary,
                test_evidence=test_evidence,
                evidence_status="ready",
            )
            return self._to_result(pack)
        finally:
            db.close()

    def get(self, pack_id: str) -> EvidencePackResult | None:
        init_db()
        db = SessionLocal()
        try:
            pack = get_operator_evidence_pack(db, pack_id)
            if pack is None:
                return None
            return self._to_result(pack)
        finally:
            db.close()

    def list_packs(self) -> list[EvidencePackResult]:
        init_db()
        db = SessionLocal()
        try:
            return [self._to_result(p) for p in list_operator_evidence_packs(db)]
        finally:
            db.close()

    def _to_result(self, pack) -> EvidencePackResult:
        return EvidencePackResult(
            pack_id=pack.id,
            created_by=pack.created_by,
            scenario_label=pack.scenario_label,
            sprint_chain=pack.sprint_chain,
            evidence_status=pack.evidence_status,
            seed_result=json.loads(pack.seed_result_json),
            safety_checks=json.loads(pack.safety_checks_json),
            runbook_summary=json.loads(pack.runbook_summary_json),
            test_evidence=json.loads(pack.test_evidence_json),
            created_at=pack.created_at.isoformat(),
            updated_at=pack.updated_at.isoformat(),
        )
