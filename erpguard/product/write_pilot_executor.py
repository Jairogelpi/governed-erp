from __future__ import annotations

import json
from datetime import datetime, timezone

from erpguard.adapters.odoo.pilot_write_client import build_pilot_write_client
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_pilot_evidence,
    create_write_pilot_run,
    get_write_pilot_request,
    get_write_pilot_run,
    get_write_pilot_run_for_request,
)
from erpguard.product.connection_context import ConnectionContextService
from erpguard.product.models import WritePilotEvidenceModel, WritePilotRunModel
from erpguard.product.write_pilot_policy import WritePilotPolicyService

_ALLOW_R1_REAL_WRITE_PILOT = False


class WritePilotExecutorService:
    def __init__(self, session) -> None:
        self.session = session

    def execute(self, request_id: str) -> WritePilotRunModel:
        req_row = get_write_pilot_request(self.session, request_id)
        if req_row is None:
            raise ObjectNotFoundError(f"Write pilot request '{request_id}' not found.")

        existing_run = get_write_pilot_run_for_request(self.session, request_id)
        if existing_run and existing_run.status in ("completed", "blocked"):
            return self._row_to_model(existing_run)

        policy = WritePilotPolicyService(self.session).check(
            skill_id=req_row.skill_id,
            target_model=req_row.target_model,
            request_id=request_id,
        )

        pre_snapshot = {
            "target_model": req_row.target_model,
            "target_res_model": req_row.target_res_model,
            "target_res_id": req_row.target_res_id,
            "notes": "Pre-execution snapshot captured",
        }

        if not _ALLOW_R1_REAL_WRITE_PILOT:
            run_row = create_write_pilot_run(
                session=self.session,
                request_id=request_id,
                skill_id=req_row.skill_id,
                status="blocked",
                executed_action="blocked_by_feature_flag",
                pre_snapshot_json=json.dumps(pre_snapshot),
                post_snapshot_json=json.dumps(pre_snapshot),
                result_json=json.dumps({
                    "blocked_reason": "ALLOW_R1_REAL_WRITE_PILOT=false",
                    "allow_r1_real_write_pilot": False,
                    "allow_generic_real_odoo_writes": False,
                }),
                policy_passed=policy.passed,
                allow_r1_real_write_pilot=False,
                finished_at=datetime.now(timezone.utc),
            )
            create_write_pilot_evidence(
                session=self.session,
                run_id=run_row.id,
                request_id=request_id,
                skill_id=req_row.skill_id,
                action_taken="blocked_by_feature_flag",
                target_model=req_row.target_model,
                target_res_model=req_row.target_res_model,
                target_res_id=str(req_row.target_res_id),
                pre_snapshot_json=json.dumps(pre_snapshot),
                post_snapshot_json=json.dumps(pre_snapshot),
                idempotency_key=req_row.idempotency_key,
                allow_r1_real_write_pilot=False,
            )
            return self._row_to_model(run_row)

        config_dict, _ = ConnectionContextService(self.session).resolve_config(req_row.skill_id)
        config = OdooConfig(**config_dict)
        client = build_pilot_write_client(config)

        payload = json.loads(req_row.payload_json)
        new_id = client.create("mail.message", {
            "model": req_row.target_res_model,
            "res_id": req_row.target_res_id,
            "body": payload.get("body", "<p>ERPGuard Sprint 8 pilot audit note.</p>"),
        })

        post_snapshot = {
            "target_model": req_row.target_model,
            "target_res_model": req_row.target_res_model,
            "target_res_id": req_row.target_res_id,
            "new_message_id": new_id,
            "notes": "Post-execution snapshot: message created",
        }

        run_row = create_write_pilot_run(
            session=self.session,
            request_id=request_id,
            skill_id=req_row.skill_id,
            status="completed",
            executed_action="mail.message.create",
            pre_snapshot_json=json.dumps(pre_snapshot),
            post_snapshot_json=json.dumps(post_snapshot),
            result_json=json.dumps({
                "new_message_id": new_id,
                "executed_action": "mail.message.create",
                "allow_r1_real_write_pilot": True,
                "allow_generic_real_odoo_writes": False,
            }),
            policy_passed=True,
            allow_r1_real_write_pilot=True,
            finished_at=datetime.now(timezone.utc),
        )
        create_write_pilot_evidence(
            session=self.session,
            run_id=run_row.id,
            request_id=request_id,
            skill_id=req_row.skill_id,
            action_taken="mail.message.create",
            target_model=req_row.target_model,
            target_res_model=req_row.target_res_model,
            target_res_id=str(req_row.target_res_id),
            pre_snapshot_json=json.dumps(pre_snapshot),
            post_snapshot_json=json.dumps(post_snapshot),
            idempotency_key=req_row.idempotency_key,
            allow_r1_real_write_pilot=True,
        )
        return self._row_to_model(run_row)

    def get(self, run_id: str) -> WritePilotRunModel:
        row = get_write_pilot_run(self.session, run_id)
        if row is None:
            raise ObjectNotFoundError(f"Write pilot run '{run_id}' not found.")
        return self._row_to_model(row)

    @staticmethod
    def _row_to_model(row) -> WritePilotRunModel:
        return WritePilotRunModel(
            run_id=row.id,
            request_id=row.request_id,
            skill_id=row.skill_id,
            status=row.status,
            executed_action=row.executed_action,
            pre_snapshot=json.loads(row.pre_snapshot_json),
            post_snapshot=json.loads(row.post_snapshot_json),
            result=json.loads(row.result_json),
            policy_passed=row.policy_passed,
            allow_r1_real_write_pilot=row.allow_r1_real_write_pilot,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            created_at=row.created_at.isoformat(),
            finished_at=row.finished_at.isoformat() if row.finished_at else None,
        )
