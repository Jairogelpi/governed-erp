from __future__ import annotations

FLOW_STEPS: list[str] = [
    "awaiting_tenant",
    "awaiting_connection",
    "run_diagnosis",
    "run_business_analysis",
    "select_opportunity",
    "create_draft",
    "review_draft",
    "compile_skill",
    "run_dry_run_proof",
    "request_approval",
    "submit_decision",
    "run_activation_gate",
    "run_live_read",
    "run_write_readiness",
    "optional_r1_write_pilot",
    "completed",
]

# Steps that require the operator to explicitly supply a value
BLOCKING_STEPS: frozenset[str] = frozenset({"awaiting_connection"})

# Steps that are safe read-only (no writes) — run-safe-readonly-path stops after run_live_read
SAFE_READONLY_BOUNDARY = "run_live_read"

_STEP_INDEX: dict[str, int] = {step: i for i, step in enumerate(FLOW_STEPS)}


def next_step(current: str) -> str | None:
    idx = _STEP_INDEX.get(current)
    if idx is None or idx + 1 >= len(FLOW_STEPS):
        return None
    return FLOW_STEPS[idx + 1]


def is_before_or_at(step: str, boundary: str) -> bool:
    return _STEP_INDEX.get(step, 999) <= _STEP_INDEX.get(boundary, -1)


def step_index(step: str) -> int:
    return _STEP_INDEX.get(step, -1)
