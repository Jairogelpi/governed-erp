"""Sprint 82 - visual workflow trace API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.visual_workflow_trace import (
    VisualWorkflowTraceAuditEventResponse,
    VisualWorkflowTraceAuditResponse,
    VisualWorkflowTraceListResponse,
    VisualWorkflowTraceRequest,
    VisualWorkflowTraceResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.visual_workflow_trace import (
    VisualWorkflowTraceAuditService,
    VisualWorkflowTraceInput,
    VisualWorkflowTraceService,
)

router = APIRouter(prefix="/v1/operator-console/visual-browser", tags=["Visual Workflow Trace"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/session/{visual_session_id}/workflow-trace", response_model=VisualWorkflowTraceResponse)
def create_visual_workflow_trace_endpoint(
    visual_session_id: str,
    request: VisualWorkflowTraceRequest,
    db: Session = Depends(get_db),
):
    result = VisualWorkflowTraceService(db).create_trace(
        VisualWorkflowTraceInput(
            visual_session_id=visual_session_id,
            created_by=request.created_by,
            workflow_name=request.workflow_name,
            workflow_goal=request.workflow_goal,
            observation_ids=request.observation_ids,
            steps=request.steps,
        )
    )
    return VisualWorkflowTraceResponse(**result.__dict__)


@router.get("/workflow-trace/{workflow_trace_id}", response_model=VisualWorkflowTraceResponse)
def get_visual_workflow_trace_endpoint(workflow_trace_id: str, db: Session = Depends(get_db)):
    result = VisualWorkflowTraceService(db).get_trace(workflow_trace_id)
    if result is None:
        return JSONResponse(status_code=404, content={"detail": "Visual workflow trace not found"})
    return VisualWorkflowTraceResponse(**result)


@router.get("/workflow-traces", response_model=VisualWorkflowTraceListResponse)
def list_visual_workflow_traces_endpoint(db: Session = Depends(get_db)):
    return VisualWorkflowTraceListResponse(
        traces=[VisualWorkflowTraceResponse(**item) for item in VisualWorkflowTraceService(db).list_traces()]
    )


@router.get("/workflow-trace-audit", response_model=VisualWorkflowTraceAuditResponse)
def get_visual_workflow_trace_audit_endpoint(db: Session = Depends(get_db)):
    result = VisualWorkflowTraceAuditService(db).get_audit()
    return VisualWorkflowTraceAuditResponse(
        events=[VisualWorkflowTraceAuditEventResponse(**event) for event in result.events]
    )
