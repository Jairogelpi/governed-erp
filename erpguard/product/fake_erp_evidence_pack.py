from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from erpguard.db.repositories import (
    create_fake_erp_execution_evidence_pack,
    get_fake_erp_execution_evidence,
    get_fake_erp_execution_evidence_pack,
    get_fake_erp_execution_record,
)
from erpguard.product.fake_erp_execution_audit import get_fake_erp_execution_audit


@dataclass(frozen=True)
class FakeERPExecutionEvidencePackResult:
    pack_id: str
    execution_id: str
    version_id: str
    skill_id: str
    dry_run_id: str
    result_snapshot: dict
    steps_snapshot: list[dict]
    safety_summary: dict
    audit_snapshot: list[dict]
    created: bool
    blocking_reasons: list[str]


def create_persisted_fake_erp_evidence_pack(*, execution_id: str, session) -> FakeERPExecutionEvidencePackResult:
    record = get_fake_erp_execution_record(session, execution_id)
    if record is None:
        return FakeERPExecutionEvidencePackResult(
            pack_id="",
            execution_id=execution_id,
            version_id="",
            skill_id="",
            dry_run_id="",
            result_snapshot={},
            steps_snapshot=[],
            safety_summary={},
            audit_snapshot=[],
            created=False,
            blocking_reasons=["execution_not_found"],
        )

    if record.status != "completed":
        return FakeERPExecutionEvidencePackResult(
            pack_id="",
            execution_id=execution_id,
            version_id=record.version_id,
            skill_id=record.skill_id,
            dry_run_id=record.dry_run_id,
            result_snapshot={},
            steps_snapshot=[],
            safety_summary={},
            audit_snapshot=[],
            created=False,
            blocking_reasons=["execution_not_completed"],
        )

    evidence = get_fake_erp_execution_evidence(session, execution_id)
    if evidence is None:
        return FakeERPExecutionEvidencePackResult(
            pack_id="",
            execution_id=execution_id,
            version_id=record.version_id,
            skill_id=record.skill_id,
            dry_run_id=record.dry_run_id,
            result_snapshot={},
            steps_snapshot=[],
            safety_summary={},
            audit_snapshot=[],
            created=False,
            blocking_reasons=["execution_evidence_missing"],
        )

    audit = get_fake_erp_execution_audit(session=session, limit=500)
    audit_entries = [
        {
            "event_id": entry.event_id,
            "execution_id": entry.execution_id,
            "version_id": entry.version_id,
            "dry_run_id": entry.dry_run_id,
            "actor": entry.actor,
            "event_type": entry.event_type,
            "status": entry.status,
            "detail": entry.detail,
            "created_at": str(entry.created_at),
        }
        for entry in audit.entries
        if entry.execution_id == execution_id
    ]

    result_snapshot = {
        "execution_id": record.id,
        "version_id": record.version_id,
        "skill_id": record.skill_id,
        "dry_run_id": record.dry_run_id,
        "execution_target": record.execution_target,
        "status": record.status,
        "step_count": record.step_count,
        "steps_executed": record.steps_executed,
        "steps_blocked": record.steps_blocked,
        "result_summary": record.result_summary,
    }
    steps_snapshot = json.loads(evidence.steps_json or "[]")
    safety_summary = json.loads(record.safety_summary_json or "{}") if record.safety_summary_json else {}

    row = create_fake_erp_execution_evidence_pack(
        session,
        pack_id=f"fepack_{uuid4().hex[:16]}",
        execution_id=record.id,
        version_id=record.version_id,
        skill_id=record.skill_id,
        dry_run_id=record.dry_run_id,
        actor_json=record.actor_json,
        inputs_json=record.inputs_json,
        result_snapshot_json=json.dumps(result_snapshot),
        steps_snapshot_json=json.dumps(steps_snapshot),
        safety_summary_json=json.dumps(safety_summary),
        audit_snapshot_json=json.dumps(audit_entries),
    )
    return FakeERPExecutionEvidencePackResult(
        pack_id=row.id,
        execution_id=row.execution_id,
        version_id=row.version_id,
        skill_id=row.skill_id,
        dry_run_id=row.dry_run_id,
        result_snapshot=result_snapshot,
        steps_snapshot=steps_snapshot,
        safety_summary=safety_summary,
        audit_snapshot=audit_entries,
        created=True,
        blocking_reasons=[],
    )


def get_fake_erp_evidence_pack_detail(*, pack_id: str, session) -> FakeERPExecutionEvidencePackResult | None:
    row = get_fake_erp_execution_evidence_pack(session, pack_id)
    if row is None:
        return None
    return FakeERPExecutionEvidencePackResult(
        pack_id=row.id,
        execution_id=row.execution_id,
        version_id=row.version_id,
        skill_id=row.skill_id,
        dry_run_id=row.dry_run_id,
        result_snapshot=json.loads(row.result_snapshot_json or "{}"),
        steps_snapshot=json.loads(row.steps_snapshot_json or "[]"),
        safety_summary=json.loads(row.safety_summary_json or "{}"),
        audit_snapshot=json.loads(row.audit_snapshot_json or "[]"),
        created=True,
        blocking_reasons=[],
    )
