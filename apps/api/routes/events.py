from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.events import CursorRequest, CursorResponse, OcelImportRequest, OcelImportResponse
from apps.api.schemas.odoo_events import OdooBridgeEventRequest, OdooIngestionResponse, OdooPollRequest, OdooPollResponse
from erpguard.domain.events.fake_generator import build_fake_ocel
from erpguard.domain.events.odoo_bridge import OdooEventIngestionService
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import Principal


router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("/odoo/webhook", response_model=OdooIngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_odoo_webhook(
    request: OdooBridgeEventRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> OdooIngestionResponse:
    result = OdooEventIngestionService(db).ingest_event(
        tenant_id=principal.tenant_id, payload=request.model_dump()
    )
    return OdooIngestionResponse(**result.__dict__)


@router.post("/odoo/poll", response_model=OdooPollResponse, status_code=status.HTTP_201_CREATED)
def ingest_odoo_poll(
    request: OdooPollRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> OdooPollResponse:
    result = OdooEventIngestionService(db).ingest_poll(
        tenant_id=principal.tenant_id,
        payloads=[event.model_dump() for event in request.events],
        cursor=request.cursor,
    )
    return OdooPollResponse(**result.__dict__)


@router.post("/ocel/import", response_model=OcelImportResponse, status_code=status.HTTP_201_CREATED)
def import_ocel(
    request: OcelImportRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> OcelImportResponse:
    result = OcelEventService(db).import_ocel(
        tenant_id=principal.tenant_id, document=request.document, source=request.source
    )
    return OcelImportResponse(**result.__dict__)


@router.get("/ocel/export")
def export_ocel(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> dict:
    return OcelEventService(db).export_ocel(tenant_id=principal.tenant_id)


@router.post("/fake-generate", response_model=OcelImportResponse, status_code=status.HTTP_201_CREATED)
def generate_fake_events(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> OcelImportResponse:
    result = OcelEventService(db).import_ocel(
        tenant_id=principal.tenant_id,
        document=build_fake_ocel(tenant_id=principal.tenant_id),
        source="fake-generator",
    )
    return OcelImportResponse(**result.__dict__)


@router.put("/cursors", response_model=CursorResponse)
def save_cursor(
    request: CursorRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> CursorResponse:
    service = OcelEventService(db)
    service.save_cursor(
        tenant_id=principal.tenant_id,
        connector_id=request.connector_id,
        stream_key=request.stream_key,
        value=request.value,
    )
    return CursorResponse(connector_id=request.connector_id, stream_key=request.stream_key, value=request.value)


@router.get("/cursors/{connector_id}/{stream_key}", response_model=CursorResponse)
def get_cursor(
    connector_id: str,
    stream_key: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> CursorResponse:
    value = OcelEventService(db).get_cursor(principal.tenant_id, connector_id, stream_key)
    return CursorResponse(connector_id=connector_id, stream_key=stream_key, value=value)
