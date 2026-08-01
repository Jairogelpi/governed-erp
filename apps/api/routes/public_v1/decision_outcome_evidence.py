"""Spec 92 Workstream D API surface (Sec 11.5).

`POST .../evidence-bundle` gathers the full manifest and, when every
required resource is present, seals it in the same call -- the spec lists
no separate seal endpoint, and `build()` is idempotent so re-posting later
(once whatever was missing exists) is the natural retry path.

The plain GET *is* the required JSON export (Sec 11.5) -- it revalidates
the stored manifest hashes before returning (Sec 11.4's "reading a bundle
must revalidate its references"); `.../verify` additionally re-fetches
every referenced resource's *current* live hash, which is the heavier,
explicitly on-demand check.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.decision_outcome_evidence import (
    EvidenceBundleCreateRequest,
    EvidenceBundleResponse,
    EvidenceBundleVerifyResponse,
)
from erpguard.application.evidence.decision_outcome_service import (
    DecisionOutcomeEvidenceService,
    EvidenceBundleNotFound,
    EvidenceIntegrityFailed,
    EvidenceSealValidationError,
)
from erpguard.domain.evidence.decision_outcome_bundle import ResourceReference, chain_hash, manifest_hash
from erpguard.domain.identity.auth import Principal

recommendation_evidence_router = APIRouter(prefix="/v1/recommendations", tags=["decision-outcome-evidence"])
evidence_router = APIRouter(prefix="/v1/decision-outcome-evidence", tags=["decision-outcome-evidence"])


@recommendation_evidence_router.post(
    "/{recommendation_id}/evidence-bundle", response_model=EvidenceBundleResponse, status_code=status.HTTP_201_CREATED
)
def create_evidence_bundle(
    recommendation_id: str,
    request: EvidenceBundleCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> EvidenceBundleResponse:
    service = DecisionOutcomeEvidenceService(db)
    row = service.build(
        tenant_id=principal.tenant_id, recommendation_id=recommendation_id, created_by=principal.user_id,
        measurement_plan_id=request.measurement_plan_id,
    )
    if row.status == "complete":
        try:
            row = service.seal(tenant_id=principal.tenant_id, bundle_id=row.id, sealed_by=principal.user_id)
        except EvidenceSealValidationError:
            pass  # bundle stays `complete`; the client can inspect why via a re-POST once resolved
    return EvidenceBundleResponse(**service.export(tenant_id=principal.tenant_id, bundle_id=row.id))


def _revalidate_stored_hashes(row) -> None:
    references = [
        ResourceReference(
            resource_type=item["resource_type"], resource_id=item["resource_id"],
            content_hash=item["content_hash"], created_at=item["created_at"],
            tenant_id=item["tenant_id"], reality_label=item["reality_label"],
        )
        for item in json.loads(row.manifest_json)
    ]
    if manifest_hash(references) != row.manifest_hash or chain_hash(references) != row.chain_hash:
        raise HTTPException(status_code=409, detail="evidence_integrity_failed")


@evidence_router.get("/{bundle_id}", response_model=EvidenceBundleResponse)
def get_evidence_bundle(
    bundle_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> EvidenceBundleResponse:
    service = DecisionOutcomeEvidenceService(db)
    try:
        row = service.get(tenant_id=principal.tenant_id, bundle_id=bundle_id)
    except EvidenceBundleNotFound as exc:
        raise HTTPException(status_code=404, detail="evidence_bundle_not_found") from exc
    _revalidate_stored_hashes(row)
    try:
        payload = service.export(tenant_id=principal.tenant_id, bundle_id=bundle_id)
    except EvidenceIntegrityFailed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EvidenceBundleResponse(**payload)


@evidence_router.get("/{bundle_id}/verify", response_model=EvidenceBundleVerifyResponse)
def verify_evidence_bundle(
    bundle_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> EvidenceBundleVerifyResponse:
    try:
        result = DecisionOutcomeEvidenceService(db).verify(tenant_id=principal.tenant_id, bundle_id=bundle_id)
    except EvidenceBundleNotFound as exc:
        raise HTTPException(status_code=404, detail="evidence_bundle_not_found") from exc
    return EvidenceBundleVerifyResponse(**result)
