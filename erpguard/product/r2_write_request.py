from __future__ import annotations

import hashlib
import json

from erpguard.adapters.odoo.r2_write_client import R2_ALLOWED_WRITE_FIELDS, R2_ALLOWED_WRITE_MODELS
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_write_pilot_request,
    get_latest_skill_version,
    get_r2_write_pilot_request,
    get_r2_write_pilot_request_by_idempotency_key,
    list_r2_write_pilot_requests_for_skill,
)
from erpguard.product.models import R2WritePilotRequestModel

_R2_TARGET_MODEL = "res.partner"


def _compute_idempotency_key(
    skill_id: str,
    target_record_id: int,
    vals: dict,
) -> str:
    raw = f"r2pilot_{skill_id}_{_R2_TARGET_MODEL}_{target_record_id}_{json.dumps(vals, sort_keys=True)}"
    return f"r2_idem_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


class R2WritePilotRequestService:
    def __init__(self, session) -> None:
        self.session = session

    def create(
        self,
        skill_id: str,
        requested_by: dict,
        approver_1: dict,
        approver_2: dict,
        target_record_id: int,
        vals: dict,
        environment: str = "staging",
    ) -> tuple[R2WritePilotRequestModel, bool]:
        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' has no compiled version.")

        disallowed_fields = set(vals.keys()) - R2_ALLOWED_WRITE_FIELDS
        if disallowed_fields:
            raise ValueError(
                f"Fields {sorted(disallowed_fields)} not allowed for R2 write. "
                f"Only {sorted(R2_ALLOWED_WRITE_FIELDS)} are permitted."
            )

        idempotency_key = _compute_idempotency_key(skill_id, target_record_id, vals)
        existing = get_r2_write_pilot_request_by_idempotency_key(self.session, idempotency_key)
        if existing:
            return self._row_to_model(existing), True

        row = create_r2_write_pilot_request(
            session=self.session,
            skill_id=skill_id,
            certification_id=None,
            requested_by_json=json.dumps(requested_by),
            approver_1_json=json.dumps(approver_1),
            approver_2_json=json.dumps(approver_2),
            target_model=_R2_TARGET_MODEL,
            target_record_id=target_record_id,
            target_fields_json=json.dumps(list(vals.keys())),
            vals_json=json.dumps(vals),
            environment=environment,
            idempotency_key=idempotency_key,
            allow_r2_real_write_pilot=False,
        )
        return self._row_to_model(row), False

    def get(self, request_id: str) -> R2WritePilotRequestModel:
        row = get_r2_write_pilot_request(self.session, request_id)
        if row is None:
            raise ObjectNotFoundError(f"R2 write pilot request '{request_id}' not found.")
        return self._row_to_model(row)

    def list_for_skill(self, skill_id: str) -> list[R2WritePilotRequestModel]:
        rows = list_r2_write_pilot_requests_for_skill(self.session, skill_id)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> R2WritePilotRequestModel:
        return R2WritePilotRequestModel(
            request_id=row.id,
            skill_id=row.skill_id,
            certification_id=row.certification_id,
            requested_by=json.loads(row.requested_by_json),
            approver_1=json.loads(row.approver_1_json),
            approver_2=json.loads(row.approver_2_json),
            target_model=row.target_model,
            target_record_id=row.target_record_id,
            target_fields=json.loads(row.target_fields_json),
            vals=json.loads(row.vals_json),
            environment=row.environment,
            idempotency_key=row.idempotency_key,
            status=row.status,
            allow_r2_real_write_pilot=row.allow_r2_real_write_pilot,
            allow_generic_real_odoo_writes=False,
            allow_r3_r4_real_writes=False,
            created_at=row.created_at.isoformat(),
        )
