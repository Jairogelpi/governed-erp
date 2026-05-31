"""Sprint 81 - visual observation snapshot API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.visual_observation import (
    VisualObservationAuditEventResponse,
    VisualObservationAuditResponse,
    VisualObservationSnapshotListResponse,
    VisualObservationSnapshotRequest,
    VisualObservationSnapshotResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.visual_observation_snapshot import (
    VisualObservationAuditService,
    VisualObservationSnapshotInput,
    VisualObservationSnapshotService,
)

router = APIRouter(
    prefix="/v1/operator-console/visual-browser",
    tags=["Visual Observation Snapshot"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/session/{visual_session_id}/observation-snapshot",
    response_model=VisualObservationSnapshotResponse,
)
def create_visual_observation_snapshot_endpoint(
    visual_session_id: str,
    request: VisualObservationSnapshotRequest,
    db: Session = Depends(get_db),
):
    result = VisualObservationSnapshotService(db).create_snapshot(
        VisualObservationSnapshotInput(
            visual_session_id=visual_session_id,
            created_by=request.created_by,
            observation_source=request.observation_source,
            screen_summary=request.screen_summary,
            dom_summary=request.dom_summary,
            visible_text=request.visible_text,
            tables=request.tables,
            forms=request.forms,
            buttons=request.buttons,
            credential_fields_detected=request.credential_fields_detected,
            dangerous_action_candidates=request.dangerous_action_candidates,
        )
    )
    return VisualObservationSnapshotResponse(**result.__dict__)


@router.get(
    "/observation-snapshot/{observation_id}",
    response_model=VisualObservationSnapshotResponse,
)
def get_visual_observation_snapshot_endpoint(
    observation_id: str,
    db: Session = Depends(get_db),
):
    result = VisualObservationSnapshotService(db).get_snapshot(observation_id)
    if result is None:
        return JSONResponse(status_code=404, content={"detail": "Visual observation snapshot not found"})
    return VisualObservationSnapshotResponse(**result)


@router.get("/observation-snapshots", response_model=VisualObservationSnapshotListResponse)
def list_visual_observation_snapshots_endpoint(db: Session = Depends(get_db)):
    return VisualObservationSnapshotListResponse(
        snapshots=[VisualObservationSnapshotResponse(**item) for item in VisualObservationSnapshotService(db).list_snapshots()]
    )


@router.get("/observation-audit", response_model=VisualObservationAuditResponse)
def get_visual_observation_audit_endpoint(db: Session = Depends(get_db)):
    result = VisualObservationAuditService(db).get_audit()
    return VisualObservationAuditResponse(
        events=[VisualObservationAuditEventResponse(**event) for event in result.events]
    )
