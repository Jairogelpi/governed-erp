from __future__ import annotations

from fastapi import APIRouter, HTTPException


from erpguard.db.session import SessionLocal
from erpguard.product.connector_credential_vault import (
    CredentialVaultContractService,
    CredentialVaultInput,
    AuthType,
)
from apps.api.schemas.connector_credentials import (
    CredentialSealRequest,
    CredentialSealResponse,
    CredentialMetadataResponse,
    CredentialRevokeResponse,
    CredentialAuditResponse,
)


router = APIRouter(
    prefix="/v1/operator-console/connectors/credentials", tags=["connector-credentials"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/seal", response_model=CredentialSealResponse)
def seal_credential(request: CredentialSealRequest):
    db = SessionLocal()
    try:
        try:
            auth_type = AuthType(request.auth_type)
        except ValueError:
            return CredentialSealResponse(
                credential_ref="",
                setup_session_id=request.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=[f"unsupported_auth_type:{request.auth_type}"],
            )

        service = CredentialVaultContractService(db)
        result = service.seal_credential(
            CredentialVaultInput(
                setup_session_id=request.setup_session_id,
                auth_type=auth_type,
                username=request.username,
                password=request.password,
                api_key=request.api_key,
                token=request.token,
                submitted_by=request.submitted_by,
            )
        )
        return result
    finally:
        db.close()


@router.get("/{credential_ref}/metadata", response_model=CredentialMetadataResponse)
def get_credential_metadata(credential_ref: str):
    db = SessionLocal()
    try:
        service = CredentialVaultContractService(db)
        result = service.get_metadata(credential_ref)
        if result is None:
            raise HTTPException(status_code=404, detail="credential_not_found")
        return result
    finally:
        db.close()


@router.post("/{credential_ref}/revoke", response_model=CredentialRevokeResponse)
def revoke_credential(credential_ref: str, revoked_by: str = "operator"):
    db = SessionLocal()
    try:
        service = CredentialVaultContractService(db)
        result = service.revoke_credential(credential_ref, revoked_by=revoked_by)
        return result
    finally:
        db.close()


@router.get("/audit", response_model=CredentialAuditResponse)
def get_credential_audit(limit: int = 50):
    db = SessionLocal()
    try:
        service = CredentialVaultContractService(db)
        return service.get_audit(limit=limit)
    finally:
        db.close()
