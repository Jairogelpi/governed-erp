from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


_RUNBOOK_OPERATIONS = [
    {
        "id": "record_session",
        "title": "Create Recording Session",
        "endpoint": "POST /v1/record-to-skill/sessions",
        "preconditions": ["Fake ERP server running at target_base_url"],
        "safety_notes": ["Fake ERP only", "No real Odoo browser opened"],
        "sprint": 21,
    },
    {
        "id": "capture_events",
        "title": "Capture Browser Events",
        "endpoint": "POST /v1/record-to-skill/sessions/{id}/events",
        "preconditions": ["Active recording session"],
        "safety_notes": ["Only known Fake ERP selectors accepted", "No coordinate fallback"],
        "sprint": 21,
    },
    {
        "id": "finish_session",
        "title": "Finish Recording Session",
        "endpoint": "POST /v1/record-to-skill/sessions/{id}/finish",
        "preconditions": ["At least one recorded event"],
        "safety_notes": ["Idempotent — safe to call multiple times"],
        "sprint": 21,
    },
    {
        "id": "generate_draft",
        "title": "Generate UI Skill Draft",
        "endpoint": "POST /v1/record-to-skill/sessions/{id}/draft",
        "preconditions": ["Finished recording session with ≥1 event"],
        "safety_notes": ["Draft is non-executable until compiled and approved"],
        "sprint": 20,
    },
    {
        "id": "compile_skill",
        "title": "Compile UI Skill",
        "endpoint": "POST /v1/record-to-skill/drafts/{id}/compile",
        "preconditions": ["Valid skill draft"],
        "safety_notes": ["Deterministic only — no LLM", "Selectors validated at compile time"],
        "sprint": 20,
    },
    {
        "id": "verified_replay",
        "title": "Verified Fail-Closed Replay",
        "endpoint": "POST /v1/record-to-skill/skills/{id}/verified-replay",
        "preconditions": ["Compiled UI skill"],
        "safety_notes": [
            "Pre/post page state verified", "Fail-closed: step not executed if check fails",
            "No automatic repair", "No LLM fallback",
        ],
        "sprint": 22,
    },
    {
        "id": "create_version",
        "title": "Create Skill Version",
        "endpoint": "POST /v1/skills/versions",
        "preconditions": ["Compiled skill"],
        "safety_notes": ["Versions are immutable once active"],
        "sprint": 23,
    },
    {
        "id": "promote_version",
        "title": "Promote Version to Candidate",
        "endpoint": "POST /v1/skills/versions/{id}/promote",
        "preconditions": ["Version in draft status", "Promotion readiness checks passed"],
        "safety_notes": ["Lifecycle transition only — no execution"],
        "sprint": 23,
    },
    {
        "id": "approve_version",
        "title": "Approve Skill Version",
        "endpoint": "POST /v1/skills/versions/{id}/approve",
        "preconditions": ["Version in candidate status"],
        "safety_notes": ["Human operator approval required", "Recorded in lifecycle audit"],
        "sprint": 23,
    },
    {
        "id": "activate_version",
        "title": "Activate Skill Version",
        "endpoint": "POST /v1/skills/versions/{id}/activate",
        "preconditions": ["Approved version"],
        "safety_notes": ["Active versions are immutable", "Only one version active per skill"],
        "sprint": 23,
    },
    {
        "id": "manual_run",
        "title": "Manual Active Skill Run",
        "endpoint": "POST /v1/skills/versions/{id}/run",
        "preconditions": ["Active version (is_active=True)", "Fake ERP target"],
        "safety_notes": [
            "Deterministic replay only", "No LLM at runtime",
            "No background worker", "Full step audit stored",
        ],
        "sprint": 24,
    },
    {
        "id": "create_schedule",
        "title": "Create Skill Schedule",
        "endpoint": "POST /v1/skills/versions/{id}/schedules",
        "preconditions": ["Active version"],
        "safety_notes": ["Minimum interval enforced at 60s", "No cron daemon created"],
        "sprint": 25,
    },
    {
        "id": "tick_scheduler",
        "title": "Manual Scheduler Tick",
        "endpoint": "POST /v1/skills/schedules/tick",
        "preconditions": ["Active schedule with next_run_at ≤ now"],
        "safety_notes": [
            "Manual trigger only — no autonomous execution",
            "Dedup window enforced", "Execution lock acquired per schedule",
            "All steps audited",
        ],
        "sprint": 25,
    },
    {
        "id": "evidence_pack",
        "title": "Assemble Evidence Pack",
        "endpoint": "POST /v1/operator/evidence-packs",
        "preconditions": ["At least one completed skill run"],
        "safety_notes": ["Read-only assembly — no new executions triggered"],
        "sprint": 26,
    },
    {
        "id": "demo_runbook",
        "title": "Get Operator Runbook",
        "endpoint": "GET /v1/operator/demo-runbook",
        "preconditions": [],
        "safety_notes": ["Static read-only — no side effects"],
        "sprint": 26,
    },
]


@dataclass(frozen=True)
class RunbookSummary:
    generated_at: str
    product: str
    operation_count: int
    sprint_chain: str
    operations: list[dict] = field(default_factory=list)
    kill_switches: list[str] = field(default_factory=list)
    safety_flags: list[dict] = field(default_factory=list)


_KILL_SWITCHES = [
    "global_kill_switch — halts all execution",
    "runtime_execution_kill_switch — halts skill runs",
    "write_pilot_kill_switch — halts write pilots",
]

_SAFETY_FLAGS = [
    {"flag": "ALLOW_GENERIC_REAL_ODOO_WRITES", "default": "false", "note": "Must stay false for demo"},
    {"flag": "ALLOW_R3_R4_REAL_WRITES", "default": "false", "note": "Hardcoded off"},
    {"flag": "ALLOW_R2_REAL_WRITE_PILOT", "default": "false", "note": "Off by default"},
    {"flag": "ALLOW_R1_REAL_WRITE_PILOT", "default": "false", "note": "Off by default"},
]


class OperatorRunbookSummaryService:
    def generate(self) -> RunbookSummary:
        return RunbookSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            product="ERPGuard — ERP Agent OS",
            operation_count=len(_RUNBOOK_OPERATIONS),
            sprint_chain="20-26",
            operations=list(_RUNBOOK_OPERATIONS),
            kill_switches=list(_KILL_SWITCHES),
            safety_flags=list(_SAFETY_FLAGS),
        )
