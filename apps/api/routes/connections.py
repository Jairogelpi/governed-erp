import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.connections import ConnectionCreateRequest, ConnectionResponse
from erpguard.canonical.enums import ERPType
from erpguard.core.preflight import PREFLIGHT_CREATED
from erpguard.db.models import Connection
from erpguard.db.repositories import create_audit_event, create_connection, get_connection, list_connections
from erpguard.db.session import SessionLocal, init_db

router = APIRouter(prefix="/v1", tags=["connections"])


@router.post("/connections", response_model=ConnectionResponse)
def create_connection_route(request: ConnectionCreateRequest):
    erp_type = _parse_erp_type(request.erp_type)
    if isinstance(erp_type, JSONResponse):
        return erp_type

    init_db()
    session = SessionLocal()
    try:
        connection = create_connection(session, request.name, erp_type, request.config)
        create_audit_event(
            session,
            connection.id,
            PREFLIGHT_CREATED,
            {"event": "connection_created", "connection_id": connection.id, "erp_type": connection.erp_type},
        )
        return _to_response(connection)
    finally:
        session.close()


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection_route(connection_id: str):
    init_db()
    session = SessionLocal()
    try:
        connection = get_connection(session, connection_id)
        if connection is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "connection_not_found", "message": f"Connection '{connection_id}' not found."}},
            )
        return _to_response(connection)
    finally:
        session.close()


@router.get("/connections", response_model=list[ConnectionResponse])
def list_connections_route():
    init_db()
    session = SessionLocal()
    try:
        return [_to_response(connection) for connection in list_connections(session)]
    finally:
        session.close()


def _parse_erp_type(value: str) -> ERPType | JSONResponse:
    try:
        return ERPType(value)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "unsupported_erp_type",
                    "message": f"Unsupported ERP type '{value}'.",
                    "details": {"erp_type": value},
                }
            },
        )


def _to_response(connection: Connection) -> dict:
    return {
        "id": connection.id,
        "name": connection.name,
        "erp_type": connection.erp_type,
        "status": connection.status,
        "config": _redact_config(json.loads(connection.config_json)),
    }


def _redact_config(config: dict) -> dict:
    redacted = dict(config)
    for key in ("api_key", "password", "token", "secret"):
        if key in redacted:
            redacted[key] = "***REDACTED***"
    return redacted
