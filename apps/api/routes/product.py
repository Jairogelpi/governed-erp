from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.product import (
    ProductAnalysisRequest,
    ProductAnalysisResponse,
    ProductAutomationDraftResponse,
    ProductAnalysisOpportunityResponse,
    ProductAnalysisSnapshotResponse,
    ProductOpportunityScanResponse,
)
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.readonly_client import build_readonly_client
from erpguard.canonical.enums import ERPType
from erpguard.core.errors import AdapterConfigurationError
from erpguard.db.repositories import get_connection, get_automation_draft, get_business_snapshot, get_opportunity, get_opportunity_scan
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.services import BusinessAnalysisService

router = APIRouter(prefix="/v1/product", tags=["product"])


@router.post("/connections/{connection_id}/analyze", response_model=ProductAnalysisResponse)
def analyze_business_connection(connection_id: str, request: ProductAnalysisRequest):
    init_db()
    session = SessionLocal()
    try:
        connection = _get_odoo_connection(session, connection_id)
        if connection is None:
            return _not_found("product_connection_not_found", f"Odoo connection '{connection_id}' not found.")
        config = _connection_config(connection)
        try:
            result = BusinessAnalysisService(session, connection, config).analyze(request)
        except Exception as exc:
            return _controlled_error(
                "product_analysis_error",
                "Could not complete business analysis.",
                connection_id,
                exc,
                status_code=503,
            )
        return result.model_dump()
    finally:
        session.close()


@router.post("/opportunities/{opportunity_id}/draft", response_model=ProductAutomationDraftResponse)
def create_automation_draft(opportunity_id: str):
    init_db()
    session = SessionLocal()
    try:
        opportunity = get_opportunity(session, opportunity_id)
        if opportunity is None:
            return _not_found("product_opportunity_not_found", f"Opportunity '{opportunity_id}' not found.")
        scan = get_opportunity_scan(session, opportunity.opportunity_scan_id)
        if scan is None:
            return _not_found("product_scan_not_found", f"Opportunity scan '{opportunity.opportunity_scan_id}' not found.")
        snapshot = get_business_snapshot(session, scan.business_snapshot_id)
        if snapshot is None:
            return _not_found("product_snapshot_not_found", f"Business snapshot '{scan.business_snapshot_id}' not found.")
        connection = get_connection(session, snapshot.connection_id)
        if connection is None or connection.erp_type != ERPType.ODOO.value:
            return _not_found("product_connection_not_found", f"Odoo connection '{snapshot.connection_id}' not found.")
        config = _connection_config(connection)
        try:
            draft = BusinessAnalysisService(session, connection, config).draft(opportunity_id)
        except Exception as exc:
            return _controlled_error(
                "product_draft_error",
                "Could not create dry-run automation draft.",
                connection.id,
                exc,
                status_code=503,
            )
        return draft.model_dump()
    finally:
        session.close()


@router.get("/snapshots/{snapshot_id}", response_model=ProductAnalysisSnapshotResponse)
def get_business_snapshot_route(snapshot_id: str):
    init_db()
    session = SessionLocal()
    try:
        row = get_business_snapshot(session, snapshot_id)
        if row is None:
            return _not_found("product_snapshot_not_found", f"Business snapshot '{snapshot_id}' not found.")
        payload = json.loads(row.snapshot_json)
        return ProductAnalysisSnapshotResponse.model_validate(
            {
                "snapshot_id": row.id,
                "connection_id": row.connection_id,
                "status": row.status,
                "read_only_mode": row.read_only_mode,
                **payload,
                "created_at": row.created_at.isoformat(),
            }
        )
    finally:
        session.close()


@router.get("/scans/{scan_id}", response_model=ProductOpportunityScanResponse)
def get_opportunity_scan_route(scan_id: str):
    init_db()
    session = SessionLocal()
    try:
        row = get_opportunity_scan(session, scan_id)
        if row is None:
            return _not_found("product_scan_not_found", f"Opportunity scan '{scan_id}' not found.")
        payload = json.loads(row.summary_json)
        return ProductOpportunityScanResponse.model_validate(
            {
                "scan_id": row.id,
                "snapshot_id": row.business_snapshot_id,
                "connection_id": row.connection_id,
                "status": row.status,
                "opportunity_count": payload.get("opportunity_count", 0),
                "signal_count": payload.get("signal_count", 0),
                "roi_summary": {
                    "roi_score_average": payload.get("roi_score_average", 0),
                },
                "created_at": row.created_at.isoformat(),
            }
        )
    finally:
        session.close()


@router.get("/drafts/{draft_id}", response_model=ProductAutomationDraftResponse)
def get_automation_draft_route(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        row = get_automation_draft(session, draft_id)
        if row is None:
            return _not_found("product_draft_not_found", f"Automation draft '{draft_id}' not found.")
        package = json.loads(row.draft_json)
        return ProductAutomationDraftResponse.model_validate(
            {
                "draft_id": row.id,
                "opportunity_id": row.opportunity_id,
                "scan_id": row.scan_id,
                "snapshot_id": row.snapshot_id,
                "connection_id": row.connection_id,
                "name": row.name,
                "description": row.description,
                "status": row.status,
                "runtime_mode": row.runtime_mode,
                "write_actions": row.write_actions,
                "draft_package": package,
                "created_at": row.created_at.isoformat(),
                "secrets_redacted": True,
            }
        )
    finally:
        session.close()


def _connection_config(connection) -> OdooConfig:
    return OdooConfig.model_validate(json.loads(connection.config_json))


def _get_odoo_connection(session, connection_id: str):
    connection = get_connection(session, connection_id)
    if connection is None or connection.erp_type != ERPType.ODOO.value:
        return None
    return connection


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _controlled_error(code: str, message: str, connection_id: str, exc: Exception, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {"connection_id": connection_id, "error_type": type(exc).__name__},
            }
        },
    )
