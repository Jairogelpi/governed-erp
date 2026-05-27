from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import create_fake_erp_execution_evidence


@dataclass(frozen=True)
class FakeERPExecutionEvidenceResult:
    evidence_pack_id: str
    execution_id: str


def persist_fake_erp_execution_evidence(
    *,
    execution_id: str,
    version_id: str,
    skill_id: str,
    dry_run_id: str,
    actor: dict,
    execution_target: str,
    inputs: dict,
    steps: list[dict],
    session,
) -> FakeERPExecutionEvidenceResult:
    safety_summary = {
        "real_erp_execution_performed": False,
        "odoo_execution_performed": False,
        "erp_writes_performed": False,
        "browser_control_performed": False,
        "mcp_execution_performed": False,
        "llm_runtime_used": False,
        "scheduler_used": False,
        "external_http_performed": False,
    }
    row = create_fake_erp_execution_evidence(
        session,
        execution_id=execution_id,
        version_id=version_id,
        skill_id=skill_id,
        dry_run_id=dry_run_id,
        actor_json=json.dumps(actor),
        execution_target=execution_target,
        inputs_json=json.dumps(inputs),
        steps_json=json.dumps(steps),
        safety_summary_json=json.dumps(safety_summary),
    )
    return FakeERPExecutionEvidenceResult(evidence_pack_id=row.id, execution_id=row.execution_id)
