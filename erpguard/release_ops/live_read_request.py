from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_live_read_execution_request,
    get_latest_approval_request_for_skill,
    get_latest_skill_version,
    get_live_read_execution_request,
    get_skill,
    list_live_read_execution_requests_for_skill,
)
from erpguard.release_ops.connection_context import ConnectionContextService
from erpguard.release_ops.idempotency import IdempotencyService
from erpguard.release_ops.models import LiveReadExecutionRequestModel


class LiveReadRequestService:
    def __init__(self, session) -> None:
        self.session = session

    def create(
        self,
        skill_id: str,
        requested_by: dict,
        inputs: dict,
    ) -> tuple[LiveReadExecutionRequestModel, bool]:
        """Create a live read execution request. Returns (model, is_duplicate)."""
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' was not found.")

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"No skill version found for skill '{skill_id}'.")

        ctx_svc = ConnectionContextService(self.session)
        ctx = ctx_svc.resolve(skill_id)
        connection_id = ctx.connection_id if ctx.resolved else None

        idem_svc = IdempotencyService(self.session)
        idem_key = idem_svc.generate_key(f"lr_{skill_id}", inputs)

        approval_row = get_latest_approval_request_for_skill(self.session, skill_id)
        approval_request_id = approval_row.id if approval_row else None

        row = create_live_read_execution_request(
            self.session,
            skill_id=skill_id,
            skill_version_id=version_row.id,
            requested_by_json=json.dumps(requested_by, default=str),
            inputs_json=json.dumps(inputs, default=str),
            idempotency_key=idem_key,
            connection_id=connection_id,
            approval_request_id=approval_request_id,
            status="pending",
        )

        is_dup, existing_req_id = idem_svc.check_and_register(
            key=idem_key,
            skill_id=skill_id,
            execution_request_id=row.id,
        )

        if is_dup and existing_req_id and existing_req_id != row.id:
            existing_lr = get_live_read_execution_request(self.session, existing_req_id)
            if existing_lr:
                return self._to_model(existing_lr), True

        return self._to_model(row), False

    def get(self, request_id: str) -> LiveReadExecutionRequestModel:
        row = get_live_read_execution_request(self.session, request_id)
        if row is None:
            raise ObjectNotFoundError(f"Live read execution request '{request_id}' not found.")
        return self._to_model(row)

    def list_for_skill(self, skill_id: str) -> list[LiveReadExecutionRequestModel]:
        rows = list_live_read_execution_requests_for_skill(self.session, skill_id)
        return [self._to_model(r) for r in rows]

    def _to_model(self, row) -> LiveReadExecutionRequestModel:
        return LiveReadExecutionRequestModel.model_validate(
            {
                "request_id": row.id,
                "skill_id": row.skill_id,
                "skill_version_id": row.skill_version_id,
                "connection_id": row.connection_id,
                "approval_request_id": row.approval_request_id,
                "requested_by": json.loads(row.requested_by_json),
                "inputs": json.loads(row.inputs_json),
                "status": row.status,
                "can_execute_real_writes": False,
                "real_erp_writes_enabled": False,
                "allow_real_odoo_reads": True,
                "idempotency_key": row.idempotency_key,
                "created_at": row.created_at.isoformat(),
            }
        )
