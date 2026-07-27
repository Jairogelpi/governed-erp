from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.processes.candidates import CandidateService, CandidateValidationError
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def test_candidate_is_immutable_after_submission_and_keeps_evidence():
    init_db()
    db = SessionLocal()
    key = f"candidate_process_{uuid4().hex}"
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", key)
    try:
        ProcessRegistry(db).register_yaml(base)
        service = CandidateService(db)
        candidate = service.create_draft(
            process_key=key, base_version="1.0.0", candidate_version="2.0.0",
            changes={"add_event": "quote.approved"}, evidence_refs=["case:so-1"], created_by="user-1",
            proposal={"reason": "structured_optional_proposal"},
        )
        submitted = service.submit(candidate.id)
        assert submitted.status == "submitted"
        assert "structured_proposal" in submitted.changes_json
        submitted.changes_json = "{}"
        with pytest.raises(ValueError, match="submitted_candidate_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_candidate_requires_valid_base_and_evidence():
    init_db()
    db = SessionLocal()
    try:
        with pytest.raises(CandidateValidationError, match="base_process_version_not_found"):
            CandidateService(db).create_draft(
                process_key="missing", base_version="1.0.0", candidate_version="2.0.0",
                changes={"x": 1}, evidence_refs=["case:missing"], created_by="user-1",
            )
    finally:
        db.close()
