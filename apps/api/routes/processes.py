from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.processes import ProcessDefinitionResponse, ProcessDiffResponse, ProcessRegisterRequest
from erpguard.domain.identity.auth import Principal
from erpguard.domain.processes.registry import ProcessDefinitionConflict, ProcessRegistry
from erpguard.domain.processes.validation import ProcessValidationError


router = APIRouter(prefix="/v1/processes", tags=["processes"])


@router.post("", response_model=ProcessDefinitionResponse, status_code=status.HTTP_201_CREATED)
def register_process(
    request: ProcessRegisterRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ProcessDefinitionResponse:
    try:
        row = ProcessRegistry(db).register_yaml(request.yaml)
    except ProcessDefinitionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProcessValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.get("/{process_key}/versions/{version}", response_model=ProcessDefinitionResponse)
def get_process(
    process_key: str,
    version: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ProcessDefinitionResponse:
    row = ProcessRegistry(db).get(process_key, version)
    if row is None:
        raise HTTPException(status_code=404, detail="process_version_not_found")
    return _response(row)


@router.get("/{process_key}/diff", response_model=ProcessDiffResponse)
def diff_process(
    process_key: str,
    from_version: str = Query(min_length=1),
    to_version: str = Query(min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ProcessDiffResponse:
    try:
        return ProcessDiffResponse(**ProcessRegistry(db).diff(process_key, from_version, to_version))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _response(row) -> ProcessDefinitionResponse:
    return ProcessDefinitionResponse(
        id=row.id,
        process_key=row.process_key,
        version=row.version,
        definition=json.loads(row.definition_json),
    )
