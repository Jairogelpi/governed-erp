from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.unified_connections import (
    UnifiedConnectionCreateRequest,
    UnifiedConnectionResponse,
)
from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.domain.connections.service import UnifiedConnectionService
from erpguard.domain.identity.auth import Principal
from erpguard.infrastructure.secrets import SecretProviderConfigurationError


router = APIRouter(prefix="/v1/unified/connections", tags=["connections"])


@router.post("", response_model=UnifiedConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_unified_connection(
    request: UnifiedConnectionCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> UnifiedConnectionResponse:
    try:
        connection = UnifiedConnectionService(db).create(
            tenant_id=principal.tenant_id,
            created_by=principal.user_id,
            name=request.name,
            connector_type=request.connector_type,
            endpoint=request.endpoint,
            auth_type=request.auth_type,
            secret=request.secret,
            metadata=request.metadata,
        )
    except SecretProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(db, connection)


@router.get("", response_model=list[UnifiedConnectionResponse])
def list_unified_connections(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> list[UnifiedConnectionResponse]:
    return [_to_response(db, item) for item in UnifiedConnectionService(db).list_for_tenant(principal.tenant_id)]


@router.get("/{connection_id}", response_model=UnifiedConnectionResponse)
def get_unified_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> UnifiedConnectionResponse:
    connection = UnifiedConnectionService(db).get_for_tenant(connection_id, principal.tenant_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return _to_response(db, connection)


def _to_response(db: Session, connection: UnifiedConnection) -> UnifiedConnectionResponse:
    secret = db.get(EncryptedSecret, connection.secret_ref)
    if secret is None:
        raise HTTPException(status_code=500, detail="connection_secret_missing")
    return UnifiedConnectionResponse(
        id=connection.id,
        tenant_id=connection.tenant_id,
        name=connection.name,
        connector_type=connection.connector_type,
        endpoint=connection.endpoint,
        auth_type=connection.auth_type,
        secret_ref=connection.secret_ref,
        secret_fingerprint=secret.fingerprint,
        status=connection.status,
        metadata=json.loads(connection.metadata_json),
        created_by=connection.created_by,
    )
