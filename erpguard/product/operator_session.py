from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_operator_session,
    get_operator_session,
    update_operator_session,
)
from erpguard.product.operator_flow_state import FLOW_STEPS, next_step


class OperatorSessionService:
    def __init__(self, session) -> None:
        self.session = session

    def create(self) -> dict:
        row = create_operator_session(self.session, current_step=FLOW_STEPS[0])
        return self._to_dict(row)

    def get(self, session_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        return self._to_dict(row)

    def select_tenant(self, session_id: str, tenant_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        known_ids = json.loads(row.known_ids_json)
        known_ids["tenant_id"] = tenant_id
        current_step = row.current_step
        if current_step == "awaiting_tenant":
            current_step = next_step(current_step) or current_step
        row = update_operator_session(
            self.session,
            session_id,
            tenant_id=tenant_id,
            current_step=current_step,
            known_ids_json=json.dumps(known_ids),
        )
        return self._to_dict(row)

    def select_connection(self, session_id: str, connection_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        known_ids = json.loads(row.known_ids_json)
        known_ids["connection_id"] = connection_id
        current_step = row.current_step
        if current_step == "awaiting_connection":
            current_step = next_step(current_step) or current_step
        row = update_operator_session(
            self.session,
            session_id,
            connection_id=connection_id,
            current_step=current_step,
            known_ids_json=json.dumps(known_ids),
        )
        return self._to_dict(row)

    def select_opportunity(self, session_id: str, opportunity_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        known_ids = json.loads(row.known_ids_json)
        known_ids["opportunity_id"] = opportunity_id
        current_step = row.current_step
        if current_step == "select_opportunity":
            current_step = next_step(current_step) or current_step
        row = update_operator_session(
            self.session,
            session_id,
            current_step=current_step,
            known_ids_json=json.dumps(known_ids),
        )
        return self._to_dict(row)

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "session_id": row.id,
            "tenant_id": row.tenant_id,
            "connection_id": row.connection_id,
            "current_step": row.current_step,
            "status": row.status,
            "known_ids": json.loads(row.known_ids_json),
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
