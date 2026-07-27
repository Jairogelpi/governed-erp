from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.domain.processes.registry import ProcessRegistry


class CandidateValidationError(ValueError):
    pass


class CandidateNotFound(KeyError):
    pass


class CandidateService:
    def __init__(self, session: Session):
        self.session = session

    def create_draft(
        self,
        *,
        process_key: str,
        base_version: str,
        candidate_version: str,
        changes: dict,
        evidence_refs: list[str],
        created_by: str,
        proposal: dict | None = None,
    ) -> ProcessCandidate:
        if ProcessRegistry(self.session).get(process_key, base_version) is None:
            raise CandidateValidationError("base_process_version_not_found")
        if not changes:
            raise CandidateValidationError("candidate_changes_required")
        refs = [ref.strip() for ref in evidence_refs if ref.strip()]
        if not refs:
            raise CandidateValidationError("evidence_refs_required")
        if any(not ref.startswith(("evt:", "case:", "variant:")) for ref in refs):
            raise CandidateValidationError("invalid_evidence_reference")
        if self.session.query(ProcessCandidate).filter_by(
            process_key=process_key, candidate_version=candidate_version
        ).one_or_none() is not None:
            raise CandidateValidationError("candidate_version_exists")
        if proposal is not None:
            changes = {**changes, "structured_proposal": proposal}
        row = ProcessCandidate(
            id=f"candidate_{uuid4().hex}", process_key=process_key,
            base_version=base_version, candidate_version=candidate_version,
            status="draft", changes_json=json.dumps(changes, sort_keys=True),
            evidence_json=json.dumps(refs, sort_keys=True), created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def submit(self, candidate_id: str) -> ProcessCandidate:
        row = self.get(candidate_id)
        if row.status != "draft":
            raise CandidateValidationError("candidate_not_draft")
        row.status = "submitted"
        row.submitted_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, candidate_id: str) -> ProcessCandidate:
        row = self.session.get(ProcessCandidate, candidate_id)
        if row is None:
            raise CandidateNotFound(candidate_id)
        return row
