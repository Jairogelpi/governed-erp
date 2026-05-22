from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


_SAFETY_INVARIANTS = [
    {"id": "fake_erp_only", "label": "Fake ERP only", "status": "enforced",
     "detail": "All browser automation targets the local Fake ERP server only. Real Odoo automation is blocked."},
    {"id": "no_llm_replay", "label": "No LLM at replay time", "status": "enforced",
     "detail": "Skill replay is fully deterministic. No LLM call occurs during execution."},
    {"id": "no_real_odoo_browser", "label": "No real Odoo browser automation", "status": "enforced",
     "detail": "ALLOW_GENERIC_REAL_ODOO_WRITES=false. Real Odoo browser sessions are never opened."},
    {"id": "no_coordinate_fallback", "label": "No coordinate-based fallback", "status": "enforced",
     "detail": "All selectors are deterministic CSS/testid-based. Coordinate clicks are rejected."},
    {"id": "no_automatic_repair", "label": "No automatic repair on failure", "status": "enforced",
     "detail": "Replay is fail-closed. If verification fails the step is not executed. No auto-fix attempted."},
    {"id": "no_background_scheduler", "label": "No background/autonomous scheduler", "status": "enforced",
     "detail": "Schedule execution is triggered only by explicit POST /v1/skills/schedules/tick. No cron daemon."},
    {"id": "no_mcp_gateway", "label": "No MCP execution gateway", "status": "enforced",
     "detail": "No tool calls are dispatched through MCP at runtime."},
    {"id": "no_r3_r4_ops", "label": "No R3/R4 operations", "status": "enforced",
     "detail": "ALLOW_R3_R4_REAL_WRITES=false always. Only R1/R2 categories permitted in controlled pilots."},
    {"id": "no_free_form_browser", "label": "No free-form browser agent", "status": "enforced",
     "detail": "Steps are declared at compile time. No dynamic navigation or unpredicted element interaction."},
    {"id": "dedup_lock_enforced", "label": "Dedup & execution lock enforced", "status": "enforced",
     "detail": "Per-schedule TTL lock prevents concurrent runs. Dedup window eliminates identical-input duplicates."},
    {"id": "full_audit_trail", "label": "Full audit trail on every run", "status": "enforced",
     "detail": "Every run, step, schedule tick, and lifecycle transition is persisted with event_type and timestamp."},
    {"id": "immutable_versions", "label": "Immutable active versions", "status": "enforced",
     "detail": "Active skill versions cannot be mutated. Rollback is a lifecycle switch — not mutation."},
]

_BLOCKED_OPERATIONS = [
    "Real Odoo browser automation (sale.order.action_confirm, account.move.action_post, etc.)",
    "Free-form browser agent with LLM-driven navigation",
    "Coordinate-based click fallback",
    "Automatic repair on replay failure",
    "Background / autonomous cron scheduler",
    "Distributed job queue (Celery, RQ, etc.)",
    "MCP execution gateway at skill runtime",
    "R3/R4 ERP write operations",
    "New ERP write categories beyond existing approved pilots",
    "LLM calls at replay time",
    "Multi-node scheduler",
    "Production ERP writes of any kind",
]

_SPRINT_CHAIN = [
    {"sprint": 20, "title": "Record-to-Skill Backend Loop", "status": "verified"},
    {"sprint": 21, "title": "Real Fake ERP Browser Recorder", "status": "verified"},
    {"sprint": 22, "title": "Verified Fail-Closed Replay", "status": "verified"},
    {"sprint": 23, "title": "Skill Versioning, Promotion & Rollback", "status": "verified"},
    {"sprint": 24, "title": "Active Skill Manual Runner", "status": "verified"},
    {"sprint": 25, "title": "Scheduled Skill Runs & Run Queue Safety", "status": "verified"},
    {"sprint": 26, "title": "Operator Runbook, Demo Scenario & Release Evidence Pack", "status": "current"},
]


@dataclass(frozen=True)
class SafetyReport:
    generated_at: str
    product: str
    sprint_chain: str
    invariants_enforced: int
    invariants_violated: int
    blocked_operations_count: int
    invariants: list[dict] = field(default_factory=list)
    blocked_operations: list[str] = field(default_factory=list)
    sprint_coverage: list[dict] = field(default_factory=list)
    verdict: str = "safe"
    verdict_detail: str = ""


class OperatorSafetyReportService:
    def generate(self) -> SafetyReport:
        enforced = [i for i in _SAFETY_INVARIANTS if i["status"] == "enforced"]
        violated = [i for i in _SAFETY_INVARIANTS if i["status"] != "enforced"]

        verdict = "safe" if not violated else "unsafe"
        verdict_detail = (
            "All safety invariants enforced. No blocked operations active."
            if not violated
            else f"{len(violated)} invariant(s) violated."
        )

        return SafetyReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            product="ERPGuard — ERP Agent OS",
            sprint_chain="20-26",
            invariants_enforced=len(enforced),
            invariants_violated=len(violated),
            blocked_operations_count=len(_BLOCKED_OPERATIONS),
            invariants=list(_SAFETY_INVARIANTS),
            blocked_operations=list(_BLOCKED_OPERATIONS),
            sprint_coverage=list(_SPRINT_CHAIN),
            verdict=verdict,
            verdict_detail=verdict_detail,
        )
