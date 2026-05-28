from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.connector_setup import (
    ConnectorSetupAuditResponse,
    ConnectorSetupSessionCreateRequest,
    ConnectorSetupSessionListResponse,
    ConnectorSetupSessionResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_setup_audit import ConnectorSetupAuditService
from erpguard.product.connector_setup_session import (
    ConnectorSetupEnvironmentType,
    ConnectorSetupInput,
    ConnectorSetupService,
)


router = APIRouter(prefix="/v1/operator-console/connectors", tags=["connector-setup"])


@router.post("/setup-session", response_model=ConnectorSetupSessionResponse)
def create_connector_setup_session_endpoint(body: ConnectorSetupSessionCreateRequest):
    init_db()
    session = SessionLocal()
    try:
        result = ConnectorSetupService(session).create_session(
            ConnectorSetupInput(
                connector_name=body.connector_name,
                erp_url=body.erp_url,
                environment_type=ConnectorSetupEnvironmentType(body.environment_type),
                submitted_by=body.submitted_by,
                credential_ref=body.credential_ref,
                raw_credentials_seen=body.raw_credentials_seen(),
            )
        )
        return result.model_dump(mode="json")
    finally:
        session.close()


@router.get("/setup-session/{session_id}", response_model=ConnectorSetupSessionResponse)
def get_connector_setup_session_endpoint(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return ConnectorSetupService(session).get_session(session_id).model_dump(mode="json")
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.get("/setup-sessions", response_model=ConnectorSetupSessionListResponse)
def list_connector_setup_sessions_endpoint():
    init_db()
    session = SessionLocal()
    try:
        return ConnectorSetupService(session).list_sessions().model_dump(mode="json")
    finally:
        session.close()


@router.get("/setup-session-audit", response_model=ConnectorSetupAuditResponse)
def list_connector_setup_session_audit_endpoint():
    init_db()
    session = SessionLocal()
    try:
        return ConnectorSetupAuditService(session).list_events().model_dump(mode="json")
    finally:
        session.close()


def _not_found(message: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "connector_setup_session_not_found", "message": message}},
    )
