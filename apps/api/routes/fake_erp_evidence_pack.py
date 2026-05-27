from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.fake_erp_evidence_pack import (
    FakeERPEvidencePackCreateRequest,
    FakeERPEvidencePackResponse,
)
from erpguard.db.repositories import (
    get_latest_fake_erp_execution_evidence_pack_for_execution as get_latest_pack_row_for_execution,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_evidence_pack import (
    create_persisted_fake_erp_evidence_pack,
    get_fake_erp_evidence_pack_detail,
)


router = APIRouter(prefix="/v1/operator-console/action-plan", tags=["fake-erp-evidence-pack"])


@router.post("/fake-erp-evidence-pack", response_model=FakeERPEvidencePackResponse)
def create_fake_erp_evidence_pack(body: FakeERPEvidencePackCreateRequest):
    init_db()
    db = SessionLocal()
    try:
        result = create_persisted_fake_erp_evidence_pack(execution_id=body.execution_id, session=db)
        return FakeERPEvidencePackResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/fake-erp-evidence-pack/{pack_id}", response_model=FakeERPEvidencePackResponse)
def get_fake_erp_evidence_pack(pack_id: str):
    init_db()
    db = SessionLocal()
    try:
        result = get_fake_erp_evidence_pack_detail(pack_id=pack_id, session=db)
        if result is None:
            raise HTTPException(status_code=404, detail="fake_erp_evidence_pack_not_found")
        return FakeERPEvidencePackResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/fake-erp-execution/{execution_id}/evidence-pack", response_model=FakeERPEvidencePackResponse)
def get_latest_fake_erp_evidence_pack_for_execution_route(execution_id: str):
    init_db()
    db = SessionLocal()
    try:
        row = get_latest_pack_row_for_execution(db, execution_id)
        if row is None:
            raise HTTPException(status_code=404, detail="fake_erp_evidence_pack_not_found")
        result = get_fake_erp_evidence_pack_detail(pack_id=row.id, session=db)
        if result is None:
            raise HTTPException(status_code=404, detail="fake_erp_evidence_pack_not_found")
        return FakeERPEvidencePackResponse(**result.__dict__)
    finally:
        db.close()
