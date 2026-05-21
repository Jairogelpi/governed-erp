from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from erpguard.db import repositories as repo
from erpguard.db.models import ConnectorReadEvidence


@dataclass
class ConnectorReadEvidenceModel:
    id: str
    auth_profile_id: str
    connector_id: str
    operation: str
    fixture_mode: bool
    record_count: int
    redacted_fields_count: int
    result_summary: dict
    policy_passed: bool
    read_only: bool
    created_at: datetime

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "auth_profile_id": self.auth_profile_id,
            "connector_id": self.connector_id,
            "operation": self.operation,
            "fixture_mode": self.fixture_mode,
            "record_count": self.record_count,
            "redacted_fields_count": self.redacted_fields_count,
            "result_summary": self.result_summary,
            "policy_passed": self.policy_passed,
            "read_only": self.read_only,
            "created_at": self.created_at.isoformat(),
        }


class ConnectorReadEvidenceService:
    def __init__(self, session: Session):
        self._session = session

    def store(
        self,
        *,
        auth_profile_id: str,
        connector_id: str,
        operation: str,
        fixture_mode: bool,
        record_count: int,
        redacted_fields_count: int,
        result_summary: dict,
        policy_passed: bool = True,
    ) -> ConnectorReadEvidenceModel:
        row = repo.create_connector_read_evidence(
            self._session,
            auth_profile_id=auth_profile_id,
            connector_id=connector_id,
            operation=operation,
            fixture_mode=fixture_mode,
            record_count=record_count,
            redacted_fields_count=redacted_fields_count,
            result_summary_json=json.dumps(result_summary),
            policy_passed=policy_passed,
        )
        return self._to_model(row)

    def get(self, evidence_id: str) -> ConnectorReadEvidenceModel | None:
        row = repo.get_connector_read_evidence(self._session, evidence_id)
        return self._to_model(row) if row else None

    def list_for_profile(self, auth_profile_id: str) -> list[ConnectorReadEvidenceModel]:
        rows = repo.list_connector_read_evidence_for_profile(self._session, auth_profile_id)
        return [self._to_model(r) for r in rows]

    def _to_model(self, row: ConnectorReadEvidence) -> ConnectorReadEvidenceModel:
        return ConnectorReadEvidenceModel(
            id=row.id,
            auth_profile_id=row.auth_profile_id,
            connector_id=row.connector_id,
            operation=row.operation,
            fixture_mode=row.fixture_mode,
            record_count=row.record_count,
            redacted_fields_count=row.redacted_fields_count,
            result_summary=json.loads(row.result_summary_json),
            policy_passed=row.policy_passed,
            read_only=row.read_only,
            created_at=row.created_at,
        )
