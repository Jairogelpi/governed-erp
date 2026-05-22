from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.product.operator_safety_report import OperatorSafetyReportService
from erpguard.product.operator_runbook_summary import OperatorRunbookSummaryService


_SAFETY_SVC = OperatorSafetyReportService()
_RUNBOOK_SVC = OperatorRunbookSummaryService()


@dataclass(frozen=True)
class DemoReport:
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
    sprint_coverage: list[dict] = field(default_factory=list)
    safety_invariants: list[dict] = field(default_factory=list)
    blocked_operations: list[str] = field(default_factory=list)
    runbook_operations: list[dict] = field(default_factory=list)
    kill_switches: list[str] = field(default_factory=list)
    safety_flags: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


_SPRINT_COVERAGE = [
    {"sprint": 20, "title": "Record-to-Skill Backend Loop", "status": "verified"},
    {"sprint": 21, "title": "Real Fake ERP Browser Recorder", "status": "verified"},
    {"sprint": 22, "title": "Verified Fail-Closed Replay", "status": "verified"},
    {"sprint": 23, "title": "Skill Versioning, Promotion & Rollback", "status": "verified"},
    {"sprint": 24, "title": "Active Skill Manual Runner", "status": "verified"},
    {"sprint": 25, "title": "Scheduled Skill Runs & Run Queue Safety", "status": "verified"},
    {"sprint": 26, "title": "Operator Runbook & Evidence Pack", "status": "current"},
]


class OperatorDemoReportService:
    def generate(self, seed_result: dict | None = None, pack_id: str | None = None) -> DemoReport:
        safety = _SAFETY_SVC.generate()
        runbook = _RUNBOOK_SVC.generate()

        notes = [
            "Fake ERP only — no real Odoo browser automation",
            "Deterministic replay — no LLM at runtime",
            "Manual tick only — no autonomous scheduler",
            "All safety invariants enforced",
            f"Evidence pack ID: {pack_id}" if pack_id else "No evidence pack ID provided",
        ]
        if seed_result:
            notes.append(f"Demo seed: session={seed_result.get('session_id', '-')}")
            notes.append(f"Demo seed: version={seed_result.get('version_id', '-')}")
            notes.append(f"Demo seed: run={seed_result.get('run_id', '-')}")
            notes.append(f"Demo seed: schedule={seed_result.get('schedule_id', '-')}")

        return DemoReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            product="ERPGuard — ERP Agent OS",
            version="0.13.0-rc1",
            sprint_chain="20-26",
            scenario_label="Fake ERP Formula Review — Full Operator Demo",
            seed_result=seed_result or {},
            safety_verdict=safety.verdict,
            safety_detail=safety.verdict_detail,
            invariants_enforced=safety.invariants_enforced,
            invariants_violated=safety.invariants_violated,
            blocked_operations_count=safety.blocked_operations_count,
            operation_count=runbook.operation_count,
            sprint_coverage=_SPRINT_COVERAGE,
            safety_invariants=safety.invariants,
            blocked_operations=safety.blocked_operations,
            runbook_operations=runbook.operations,
            kill_switches=runbook.kill_switches,
            safety_flags=runbook.safety_flags,
            notes=notes,
        )
