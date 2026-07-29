from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.variants import CaseTraceResponse, TraceEventResponse, VariantSummaryResponse
from erpguard.domain.identity.auth import Principal
from erpguard.domain.variants.discovery import VariantDiscoveryService


router = APIRouter(prefix="/v1/variants", tags=["variants"])


@router.get("", response_model=list[VariantSummaryResponse])
def list_variants(
    object_type: str = "sales_order",
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> list[VariantSummaryResponse]:
    return [
        VariantSummaryResponse(
            variant_id=item.variant_id,
            sequence=list(item.sequence),
            case_count=item.case_count,
            duration_seconds=item.duration_seconds,
            case_ids=list(item.case_ids),
        )
        for item in VariantDiscoveryService(db).discover(
            tenant_id=principal.tenant_id, object_type=object_type
        )
    ]


@router.get("/cases/{case_id}", response_model=CaseTraceResponse)
def get_case_trace(
    case_id: str,
    object_type: str = "sales_order",
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> CaseTraceResponse:
    try:
        trace = VariantDiscoveryService(db).case_trace(
            tenant_id=principal.tenant_id, case_id=case_id, object_type=object_type
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseTraceResponse(
        case_id=trace.case_id,
        object_type=trace.object_type,
        variant_id=trace.variant_id,
        duration_seconds=trace.duration_seconds,
        events=[TraceEventResponse(**event.__dict__) for event in trace.events],
    )


@router.get("/dashboard", response_class=HTMLResponse)
def variants_dashboard(
    principal: Principal = Depends(require_role("viewer")),
) -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html><head><title>Variant Discovery</title></head>
        <body><main><h1>Variant Discovery</h1><p>Tenant-scoped process variants.</p>
        <p>Use <code>/v1/variants</code> for variant summaries and
        <code>/v1/variants/cases/{case_id}</code> for a selected trace.</p></main></body></html>"""
    )
