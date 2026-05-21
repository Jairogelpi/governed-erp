from __future__ import annotations

from pydantic import BaseModel

from erpguard.product.scope_registry import ScopeRegistry


class OAuthReadiness(BaseModel):
    connector_id: str
    auth_type: str
    oauth_ready: bool = False
    oauth_flow_enabled: bool = False
    provider_api_calls_enabled: bool = False
    readiness_status: str = "placeholder_only"
    message: str = "OAuth metadata is prepared, but no productive OAuth flow or provider API call is enabled."


class OAuthReadinessService:
    def readiness_for(self, connector_id: str, auth_type: str) -> OAuthReadiness:
        scope = ScopeRegistry().get(connector_id)
        if scope is None:
            return OAuthReadiness(connector_id=connector_id, auth_type=auth_type, readiness_status="connector_unknown")
        return OAuthReadiness(connector_id=connector_id, auth_type=auth_type)
