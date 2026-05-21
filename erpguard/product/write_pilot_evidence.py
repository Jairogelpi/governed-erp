from __future__ import annotations

import json

from erpguard.db.repositories import list_write_pilot_evidence_for_run
from erpguard.product.models import WritePilotEvidenceModel


class WritePilotEvidenceService:
    def __init__(self, session) -> None:
        self.session = session

    def list_for_run(self, run_id: str) -> list[WritePilotEvidenceModel]:
        rows = list_write_pilot_evidence_for_run(self.session, run_id)
        return [
            WritePilotEvidenceModel(
                evidence_id=r.id,
                run_id=r.run_id,
                request_id=r.request_id,
                skill_id=r.skill_id,
                action_taken=r.action_taken,
                target_model=r.target_model,
                target_res_model=r.target_res_model,
                target_res_id=r.target_res_id,
                pre_snapshot=json.loads(r.pre_snapshot_json),
                post_snapshot=json.loads(r.post_snapshot_json),
                idempotency_key=r.idempotency_key,
                allow_r1_real_write_pilot=r.allow_r1_real_write_pilot,
                allow_generic_real_odoo_writes=False,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]
