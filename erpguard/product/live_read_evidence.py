from __future__ import annotations

import json

from erpguard.db.repositories import list_live_read_evidence_for_run
from erpguard.product.models import LiveReadEvidenceModel


class LiveReadEvidenceService:
    def __init__(self, session) -> None:
        self.session = session

    def list_for_run(self, live_read_run_id: str) -> list[LiveReadEvidenceModel]:
        rows = list_live_read_evidence_for_run(self.session, live_read_run_id)
        return [self._to_model(r) for r in rows]

    def _to_model(self, row) -> LiveReadEvidenceModel:
        return LiveReadEvidenceModel.model_validate(
            {
                "evidence_id": row.id,
                "live_read_run_id": row.live_read_run_id,
                "execution_request_id": row.execution_request_id,
                "skill_id": row.skill_id,
                "step_id": row.step_id,
                "odoo_model": row.odoo_model,
                "odoo_method": row.odoo_method,
                "query_summary": json.loads(row.query_summary_json),
                "records_fetched": row.records_fetched,
                "result_summary": json.loads(row.result_summary_json),
                "read_only": row.read_only,
                "created_at": row.created_at.isoformat(),
            }
        )
