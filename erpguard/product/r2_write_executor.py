from __future__ import annotations

import json
from datetime import datetime, timezone

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.r2_write_client import build_r2_write_client
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_write_pilot_evidence,
    create_r2_write_pilot_run,
    get_r2_write_pilot_request,
    get_r2_write_pilot_run,
    get_r2_write_pilot_run_for_request,
    list_r2_write_pilot_evidence_for_run,
)
from erpguard.product.connection_context import ConnectionContextService
from erpguard.product.models import R2WritePilotEvidenceModel, R2WritePilotRunModel
from erpguard.product.r2_write_policy import R2WritePilotPolicyService

_ALLOW_R2_REAL_WRITE_PILOT = False


def _build_rollback_instructions(
    target_model: str,
    target_record_id: int,
    pre_snapshot: dict,
) -> dict:
    return {
        "action": "re-write original field values",
        "model": target_model,
        "record_id": target_record_id,
        "restore_vals": pre_snapshot,
        "odoo_call": f"env['{target_model}'].browse({target_record_id}).write({pre_snapshot})",
        "notes": "Execute this in an Odoo shell (staging) to restore the previous state.",
    }


class R2WritePilotExecutorService:
    def __init__(self, session) -> None:
        self.session = session

    def execute(self, request_id: str) -> R2WritePilotRunModel:
        req_row = get_r2_write_pilot_request(self.session, request_id)
        if req_row is None:
            raise ObjectNotFoundError(f"R2 write pilot request '{request_id}' not found.")

        existing_run = get_r2_write_pilot_run_for_request(self.session, request_id)
        if existing_run and existing_run.status in ("completed", "blocked"):
            return self._row_to_model(existing_run)

        approver_1 = json.loads(req_row.approver_1_json)
        approver_2 = json.loads(req_row.approver_2_json)
        target_fields = json.loads(req_row.target_fields_json)

        policy = R2WritePilotPolicyService(self.session).check(
            skill_id=req_row.skill_id,
            request_id=request_id,
            target_model=req_row.target_model,
            target_fields=target_fields,
            environment=req_row.environment,
            approver_1_id=approver_1.get("id", ""),
            approver_2_id=approver_2.get("id", ""),
        )

        pre_snapshot: dict = {
            "target_model": req_row.target_model,
            "target_record_id": req_row.target_record_id,
            "notes": "Pre-execution snapshot — field values before R2 write",
        }

        if not _ALLOW_R2_REAL_WRITE_PILOT:
            run_row = create_r2_write_pilot_run(
                session=self.session,
                request_id=request_id,
                skill_id=req_row.skill_id,
                status="blocked",
                executed_action="blocked_by_feature_flag",
                pre_snapshot_json=json.dumps(pre_snapshot),
                post_snapshot_json=json.dumps(pre_snapshot),
                result_json=json.dumps({
                    "blocked_reason": "ALLOW_R2_REAL_WRITE_PILOT=false",
                    "allow_r2_real_write_pilot": False,
                    "allow_generic_real_odoo_writes": False,
                    "policy_violations": [v.model_dump() for v in policy.violations],
                }),
                policy_passed=policy.passed,
                allow_r2_real_write_pilot=False,
                finished_at=datetime.now(timezone.utc),
            )
            rollback = _build_rollback_instructions(
                req_row.target_model, req_row.target_record_id, {}
            )
            create_r2_write_pilot_evidence(
                session=self.session,
                run_id=run_row.id,
                request_id=request_id,
                skill_id=req_row.skill_id,
                action_taken="blocked_by_feature_flag",
                target_model=req_row.target_model,
                target_record_id=str(req_row.target_record_id),
                pre_snapshot_json=json.dumps(pre_snapshot),
                post_snapshot_json=json.dumps(pre_snapshot),
                rollback_instructions_json=json.dumps(rollback),
                idempotency_key=req_row.idempotency_key,
                allow_r2_real_write_pilot=False,
            )
            return self._row_to_model(run_row)

        # Feature flag enabled — capture real pre-snapshot and execute
        config_dict, _ = ConnectionContextService(self.session).resolve_config(req_row.skill_id)
        config = OdooConfig(**config_dict)
        client = build_r2_write_client(config)

        vals = json.loads(req_row.vals_json)
        live_pre = client.read_fields(req_row.target_model, req_row.target_record_id, target_fields)
        pre_snapshot = {
            **pre_snapshot,
            "field_values": live_pre,
        }

        client.write(req_row.target_model, req_row.target_record_id, vals)

        live_post = client.read_fields(req_row.target_model, req_row.target_record_id, target_fields)
        post_snapshot = {
            "target_model": req_row.target_model,
            "target_record_id": req_row.target_record_id,
            "field_values": live_post,
            "notes": "Post-execution snapshot — field values after R2 write",
        }

        rollback = _build_rollback_instructions(
            req_row.target_model, req_row.target_record_id, live_pre
        )

        run_row = create_r2_write_pilot_run(
            session=self.session,
            request_id=request_id,
            skill_id=req_row.skill_id,
            status="completed",
            executed_action=f"{req_row.target_model}.write",
            pre_snapshot_json=json.dumps(pre_snapshot),
            post_snapshot_json=json.dumps(post_snapshot),
            result_json=json.dumps({
                "executed_action": f"{req_row.target_model}.write",
                "vals_written": vals,
                "allow_r2_real_write_pilot": True,
                "allow_generic_real_odoo_writes": False,
            }),
            policy_passed=True,
            allow_r2_real_write_pilot=True,
            finished_at=datetime.now(timezone.utc),
        )
        create_r2_write_pilot_evidence(
            session=self.session,
            run_id=run_row.id,
            request_id=request_id,
            skill_id=req_row.skill_id,
            action_taken=f"{req_row.target_model}.write",
            target_model=req_row.target_model,
            target_record_id=str(req_row.target_record_id),
            pre_snapshot_json=json.dumps(pre_snapshot),
            post_snapshot_json=json.dumps(post_snapshot),
            rollback_instructions_json=json.dumps(rollback),
            idempotency_key=req_row.idempotency_key,
            allow_r2_real_write_pilot=True,
        )
        return self._row_to_model(run_row)

    def get(self, run_id: str) -> R2WritePilotRunModel:
        row = get_r2_write_pilot_run(self.session, run_id)
        if row is None:
            raise ObjectNotFoundError(f"R2 write pilot run '{run_id}' not found.")
        return self._row_to_model(row)

    def get_evidence(self, run_id: str) -> list[R2WritePilotEvidenceModel]:
        rows = list_r2_write_pilot_evidence_for_run(self.session, run_id)
        return [self._ev_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> R2WritePilotRunModel:
        return R2WritePilotRunModel(
            run_id=row.id,
            request_id=row.request_id,
            skill_id=row.skill_id,
            status=row.status,
            executed_action=row.executed_action,
            pre_snapshot=json.loads(row.pre_snapshot_json),
            post_snapshot=json.loads(row.post_snapshot_json),
            result=json.loads(row.result_json),
            policy_passed=row.policy_passed,
            allow_r2_real_write_pilot=row.allow_r2_real_write_pilot,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            created_at=row.created_at.isoformat(),
            finished_at=row.finished_at.isoformat() if row.finished_at else None,
        )

    @staticmethod
    def _ev_to_model(row) -> R2WritePilotEvidenceModel:
        return R2WritePilotEvidenceModel(
            evidence_id=row.id,
            run_id=row.run_id,
            request_id=row.request_id,
            skill_id=row.skill_id,
            action_taken=row.action_taken,
            target_model=row.target_model,
            target_record_id=row.target_record_id,
            pre_snapshot=json.loads(row.pre_snapshot_json),
            post_snapshot=json.loads(row.post_snapshot_json),
            rollback_instructions=json.loads(row.rollback_instructions_json),
            idempotency_key=row.idempotency_key,
            allow_r2_real_write_pilot=row.allow_r2_real_write_pilot,
            allow_generic_real_odoo_writes=False,
            created_at=row.created_at.isoformat(),
        )
