from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.processes.candidates import CandidateEvidenceNotFound, CandidateService
from erpguard.domain.processes.registry import ProcessRegistry
from erpguard.domain.variants.discovery import VariantDiscoveryService


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _seed(db, tenant_id: str, process_key: str) -> None:
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
    ProcessRegistry(db).register_yaml(base)
    OcelEventService(db).import_ocel(
        tenant_id=tenant_id,
        source="candidate-evidence-test",
        document={
            "ocel:objects": {"so-1": {"ocel:type": "sale_order", "ocel:ovmap": {}}},
            "ocel:events": {
                "e-1": {
                    "ocel:activity": "sales.quote.created",
                    "ocel:timestamp": "2026-01-01T00:00:00Z",
                    "ocel:omap": ["so-1"],
                    "ocel:vmap": {},
                },
            },
        },
    )


def _create(db, tenant_id: str, process_key: str, evidence_ref: str):
    return CandidateService(db).create_draft(
        tenant_id=tenant_id,
        process_key=process_key,
        base_version="1.0.0",
        candidate_version=f"2.0.{uuid4().hex[:8]}",
        changes={"add_event": {"name": "sales.quote.approved", "object": "quotation"}},
        evidence_refs=[evidence_ref],
        created_by="evidence-user",
    )


def test_variant_evidence_is_resolved_from_tenant_projection():
    init_db()
    db = SessionLocal()
    tenant_id = f"variant-evidence-{uuid4().hex}"
    process_key = f"candidate-evidence-process-{uuid4().hex}"
    try:
        _seed(db, tenant_id, process_key)
        variant_id = VariantDiscoveryService(db).discover(
            tenant_id=tenant_id, object_type="sales_order"
        )[0].variant_id
        candidate = _create(db, tenant_id, process_key, f"variant:{variant_id}")
        assert candidate.validation_status == "valid"
    finally:
        db.close()


def test_evidence_from_another_tenant_is_not_found():
    init_db()
    db = SessionLocal()
    process_key = f"candidate-cross-evidence-{uuid4().hex}"
    tenant_a = f"evidence-a-{uuid4().hex}"
    tenant_b = f"evidence-b-{uuid4().hex}"
    try:
        _seed(db, tenant_a, process_key)
        # The same canonical ID shape exists only in tenant B for this lookup.
        _seed(db, tenant_b, f"candidate-cross-evidence-b-{uuid4().hex}")
        with pytest.raises(CandidateEvidenceNotFound, match="candidate_evidence_not_found"):
            _create(db, tenant_a, process_key, f"evt:evt_{tenant_b}_e-1")
    finally:
        db.close()
