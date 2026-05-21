from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from erpguard.product.connector_auth_profile import ConnectorAuthProfileService, ConnectorAuthProfileModel


class CredentialRotationService:
    def __init__(self, session: Session):
        self.service = ConnectorAuthProfileService(session)

    def rotate(self, profile_id: str, credential: dict[str, Any] | None, actor: dict[str, Any] | None = None) -> ConnectorAuthProfileModel:
        return self.service.rotate(profile_id, credential, actor=actor)
