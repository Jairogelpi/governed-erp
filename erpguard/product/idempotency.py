from __future__ import annotations

import hashlib
import json

from erpguard.db.repositories import get_or_create_idempotency_key


class IdempotencyService:
    def __init__(self, session) -> None:
        self.session = session

    def generate_key(self, skill_id: str, inputs: dict) -> str:
        payload = json.dumps({"skill_id": skill_id, "inputs": inputs}, sort_keys=True, default=str)
        return f"idem_{hashlib.sha256(payload.encode()).hexdigest()[:32]}"

    def check_and_register(self, key: str, skill_id: str, execution_request_id: str) -> tuple[bool, str | None]:
        row, is_duplicate = get_or_create_idempotency_key(
            self.session,
            key=key,
            skill_id=skill_id,
            execution_request_id=execution_request_id,
        )
        if is_duplicate:
            return True, row.execution_request_id
        return False, None
