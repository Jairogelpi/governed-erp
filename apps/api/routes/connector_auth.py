from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.connector_auth import (
    ConnectorAuthProfileListResponse,
    ConnectorAuthProfileResponse,
    ConnectorCredentialAuditResponse,
    ConnectorScopeListResponse,
    ConnectorTestRequest,
    ConnectorTestResponse,
    CreateConnectorAuthProfileRequest,
    RevokeConnectorAuthProfileRequest,
    RotateConnectorAuthProfileRequest,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_auth_profile import ConnectorAuthProfileService
from erpguard.product.scope_registry import ScopeRegistry


router = APIRouter(prefix="/v1/connectors", tags=["connector-auth"])


@router.post("/auth-profiles", response_model=ConnectorAuthProfileResponse)
def create_auth_profile(request: CreateConnectorAuthProfileRequest):
    init_db()
    session = SessionLocal()
    try:
        return ConnectorAuthProfileService(session).create_profile(
            connector_id=request.connector_id,
            display_name=request.display_name,
            auth_type=request.auth_type,
            requested_scopes=request.requested_scopes,
            credential=request.credential,
            created_by=request.created_by,
        ).model_dump()
    finally:
        session.close()


@router.get("/auth-profiles", response_model=ConnectorAuthProfileListResponse)
def list_auth_profiles():
    return _with_auth_service(lambda service: {"profiles": [profile.model_dump() for profile in service.list_profiles()]})


@router.get("/auth-profiles/{profile_id}", response_model=ConnectorAuthProfileResponse)
def get_auth_profile(profile_id: str):
    return _with_auth_service(lambda service: service.get_profile(profile_id))


@router.post("/auth-profiles/{profile_id}/test", response_model=ConnectorTestResponse)
def test_auth_profile(profile_id: str, request: ConnectorTestRequest):
    return _with_auth_service(lambda service: service.simulate_test(profile_id, actor=request.actor))


@router.post("/auth-profiles/{profile_id}/rotate", response_model=ConnectorAuthProfileResponse)
def rotate_auth_profile(profile_id: str, request: RotateConnectorAuthProfileRequest):
    return _with_auth_service(lambda service: service.rotate(profile_id, credential=request.credential, actor=request.actor))


@router.post("/auth-profiles/{profile_id}/revoke", response_model=ConnectorAuthProfileResponse)
def revoke_auth_profile(profile_id: str, request: RevokeConnectorAuthProfileRequest):
    return _with_auth_service(lambda service: service.revoke(profile_id, actor=request.actor))


@router.get("/auth-profiles/{profile_id}/audit", response_model=ConnectorCredentialAuditResponse)
def get_auth_profile_audit(profile_id: str):
    return _with_auth_service(lambda service: {"profile_id": profile_id, "events": [event.model_dump() for event in service.audit(profile_id)]})


@router.get("/scopes", response_model=ConnectorScopeListResponse)
def list_connector_scopes():
    return {"scopes": [scope.model_dump() for scope in ScopeRegistry().list_scopes()]}


def _with_auth_service(callback):
    init_db()
    session = SessionLocal()
    try:
        service = ConnectorAuthProfileService(session)
        try:
            result = callback(service)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
        return result.model_dump() if hasattr(result, "model_dump") else result
    finally:
        session.close()


def _not_found(message: str):
    return JSONResponse(status_code=404, content={"error": {"code": "auth_profile_not_found", "message": message}})
