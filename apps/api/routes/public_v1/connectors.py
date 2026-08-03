"""Public Connector SDK v2 definition and safe connection-test boundary."""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.connectors import (
    ConnectorAuthSchemaResponse,
    ConnectorCapabilityResponse,
    ConnectorDefinitionResponse,
    ConnectorTestRequest,
    ConnectorTestResponse,
    ModelFieldResponse,
    ModelSchemaResponse,
)
from erpguard.application.connectors.service import (
    ConnectionNotFound,
    ConnectorApplicationService,
    ConnectorConnectionMismatch,
    ConnectorNotFound,
    ConnectorOperationUnavailable,
)
from erpguard.connectors.sdk.plugin import ConnectorPlugin
from erpguard.domain.identity.auth import Principal


router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorDefinitionResponse])
def list_connectors(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> list[ConnectorDefinitionResponse]:
    return [_definition_response(plugin) for plugin in ConnectorApplicationService(db).registry.list()]


@router.get("/{connector_id}", response_model=ConnectorDefinitionResponse)
def get_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ConnectorDefinitionResponse:
    service = ConnectorApplicationService(db)
    try:
        metadata = service.registry.get(connector_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connector_not_found") from exc
    return _definition_response(metadata)


@router.post("/{connector_id}/test", response_model=ConnectorTestResponse)
async def test_connector(
    connector_id: str,
    request: ConnectorTestRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ConnectorTestResponse:
    service = ConnectorApplicationService(db)
    try:
        result = await service.test_connection(
            tenant_id=principal.tenant_id,
            connection_id=request.connection_id,
            connector_id=connector_id,
        )
    except ConnectorNotFound as exc:
        raise HTTPException(status_code=404, detail="connector_not_found") from exc
    except ConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="connection_not_found") from exc
    except ConnectorConnectionMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConnectorOperationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ConnectorTestResponse(
        connector_id=connector_id,
        connection_id=request.connection_id,
        status=result.status,
        summary=result.summary,
        safety_flags=result.safety_flags.model_dump(mode="json"),
    )


_MODEL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


@router.get(
    "/{connector_id}/connections/{connection_id}/schema/{model}",
    response_model=ModelSchemaResponse,
)
async def get_model_schema(
    connector_id: str,
    connection_id: str,
    model: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ModelSchemaResponse:
    if not _MODEL_IDENTIFIER.match(model):
        raise HTTPException(status_code=400, detail="invalid_model_identifier")
    service = ConnectorApplicationService(db)
    try:
        fields = await service.discover_model_fields(
            tenant_id=principal.tenant_id,
            connection_id=connection_id,
            connector_id=connector_id,
            model=model,
        )
    except ConnectorNotFound as exc:
        raise HTTPException(status_code=404, detail="connector_not_found") from exc
    except ConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="connection_not_found") from exc
    except ConnectorConnectionMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConnectorOperationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ModelSchemaResponse(
        connector_id=connector_id,
        connection_id=connection_id,
        model=model,
        fields=[
            ModelFieldResponse(
                name=name,
                type=str(definition.get("type", "")),
                string=str(definition.get("string", "")),
                readonly=bool(definition.get("readonly", False)),
            )
            for name, definition in sorted(fields.items())
        ],
    )


def _definition_response(plugin: ConnectorPlugin) -> ConnectorDefinitionResponse:
    return ConnectorDefinitionResponse(
        **plugin.metadata.model_dump(mode="json"),
        auth_schemas=[
            ConnectorAuthSchemaResponse(**item.model_dump(mode="json"))
            for item in plugin.auth_schemas()
        ],
        capabilities=[
            ConnectorCapabilityResponse(**item.model_dump(mode="json"))
            for item in plugin.capability_definitions()
        ],
    )
