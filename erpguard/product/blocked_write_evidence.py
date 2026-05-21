from __future__ import annotations

import json

from erpguard.db.repositories import list_blocked_write_evidence_for_run
from erpguard.product.models import BlockedWriteEvidenceModel


class BlockedWriteEvidenceService:
    def __init__(self, session) -> None:
        self.session = session

    def list_for_run(self, execution_run_id: str) -> list[BlockedWriteEvidenceModel]:
        rows = list_blocked_write_evidence_for_run(self.session, execution_run_id)
        return [self._to_model(r) for r in rows]

    def _to_model(self, row) -> BlockedWriteEvidenceModel:
        return BlockedWriteEvidenceModel.model_validate(
            {
                "evidence_id": row.id,
                "execution_run_id": row.execution_run_id,
                "execution_request_id": row.execution_request_id,
                "skill_id": row.skill_id,
                "attempted_model": row.attempted_model,
                "attempted_method": row.attempted_method,
                "attempted_args": json.loads(row.attempted_args_json),
                "blocked_reason": row.blocked_reason,
                "created_at": row.created_at.isoformat(),
            }
        )
