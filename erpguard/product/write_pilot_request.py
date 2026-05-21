from __future__ import annotations

import hashlib
import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_pilot_request,
    get_latest_skill_version,
    get_write_pilot_request,
    get_write_pilot_request_by_idempotency_key,
    list_write_pilot_requests_for_skill,
)
from erpguard.product.models import WritePilotRequestModel

_PILOT_TARGET_MODEL = "mail.message"


def _compute_idempotency_key(skill_id: str, target_res_model: str, target_res_id: int, payload: dict) -> str:
    body = payload.get("body", "")
    raw = f"pilot_{skill_id}_{target_res_model}_{target_res_id}_{body}"
    return f"wp_idem_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


class WritePilotRequestService:
    def __init__(self, session) -> None:
        self.session = session

    def create(
        self,
        skill_id: str,
        requested_by: dict,
        approver_1: dict,
        approver_2: dict,
        target_res_model: str,
        target_res_id: int,
        payload: dict,
    ) -> tuple[WritePilotRequestModel, bool]:
        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' has no compiled version.")

        idempotency_key = _compute_idempotency_key(skill_id, target_res_model, target_res_id, payload)

        existing = get_write_pilot_request_by_idempotency_key(self.session, idempotency_key)
        if existing:
            return self._row_to_model(existing), True

        row = create_write_pilot_request(
            session=self.session,
            skill_id=skill_id,
            certification_id=None,
            requested_by_json=json.dumps(requested_by),
            approver_1_json=json.dumps(approver_1),
            approver_2_json=json.dumps(approver_2),
            target_model=_PILOT_TARGET_MODEL,
            target_res_model=target_res_model,
            target_res_id=target_res_id,
            payload_json=json.dumps(payload),
            idempotency_key=idempotency_key,
        )
        return self._row_to_model(row), False

    def get(self, request_id: str) -> WritePilotRequestModel:
        row = get_write_pilot_request(self.session, request_id)
        if row is None:
            raise ObjectNotFoundError(f"Write pilot request '{request_id}' not found.")
        return self._row_to_model(row)

    def list_for_skill(self, skill_id: str) -> list[WritePilotRequestModel]:
        rows = list_write_pilot_requests_for_skill(self.session, skill_id)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> WritePilotRequestModel:
        return WritePilotRequestModel(
            request_id=row.id,
            skill_id=row.skill_id,
            certification_id=row.certification_id,
            requested_by=json.loads(row.requested_by_json),
            approver_1=json.loads(row.approver_1_json),
            approver_2=json.loads(row.approver_2_json),
            target_model=row.target_model,
            target_res_model=row.target_res_model,
            target_res_id=row.target_res_id,
            payload=json.loads(row.payload_json),
            idempotency_key=row.idempotency_key,
            status=row.status,
            allow_r1_real_write_pilot=row.allow_r1_real_write_pilot,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            created_at=row.created_at.isoformat(),
        )
