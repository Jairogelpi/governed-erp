"""Proof of Improvement API (master spec section 17 / 23.5 / Phase 13).

No blanket prefix: the create route is nested under /v1/replays/... per
spec 23.5, the read route under /v1/proofs/... -- same "explicit full path
per route" approach used by apps/api/routes/public_v1/replays.py for its
/v1/processes/... create route.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.proofs import ProofCreateRequest, ProofResponse
from erpguard.domain.identity.auth import Principal
from erpguard.domain.proofs.service import (
    ProofNotFound,
    ProofService,
    ProofValidationError,
    ReplayNotFoundForProof,
)

router = APIRouter(tags=["proofs"])


@router.post(
    "/v1/replays/{replay_id}/proofs",
    response_model=ProofResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_proof(
    replay_id: str,
    request: ProofCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ProofResponse:
    try:
        row = ProofService(db).generate_proof(
            tenant_id=principal.tenant_id,
            baseline_replay_id=request.baseline_replay_id,
            candidate_replay_id=replay_id,
            benchmark_version=request.benchmark_version,
        )
    except ReplayNotFoundForProof as exc:
        raise HTTPException(status_code=404, detail="replay_not_found") from exc
    except ProofValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.get("/v1/proofs/{proof_id}", response_model=ProofResponse)
def get_proof(
    proof_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ProofResponse:
    try:
        row = ProofService(db).get_proof(tenant_id=principal.tenant_id, proof_id=proof_id)
    except ProofNotFound as exc:
        raise HTTPException(status_code=404, detail="proof_not_found") from exc
    return _response(row)


def _response(row) -> ProofResponse:
    return ProofResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        baseline_replay_id=row.baseline_replay_id,
        candidate_replay_id=row.candidate_replay_id,
        dataset_version=row.dataset_version,
        benchmark_version=row.benchmark_version,
        metric_comparisons=json.loads(row.metric_comparisons_json),
        regressions=json.loads(row.regressions_json),
        safety_summary=json.loads(row.safety_summary_json),
        reproducibility_summary=json.loads(row.reproducibility_summary_json),
        evidence_refs=json.loads(row.evidence_refs_json),
        recommendation=row.recommendation,
        recommendation_basis=json.loads(row.recommendation_basis_json),
        limitations=json.loads(row.limitations_json),
        content_hash=row.content_hash,
        generated_at=row.generated_at.isoformat(),
    )
