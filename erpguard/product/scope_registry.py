from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectorScopeDefinition(BaseModel):
    connector_id: str
    display_name: str
    available_scopes: list[str] = Field(default_factory=list)
    default_scopes: list[str] = Field(default_factory=list)
    oauth_readiness: str = "placeholder_only"
    oauth_flow_enabled: bool = False
    provider_api_calls_enabled: bool = False


class ScopeRegistry:
    def list_scopes(self) -> list[ConnectorScopeDefinition]:
        return list(SCOPES)

    def get(self, connector_id: str) -> ConnectorScopeDefinition | None:
        return next((item for item in SCOPES if item.connector_id == connector_id), None)


SCOPES = [
    ConnectorScopeDefinition(
        connector_id="odoo",
        display_name="Odoo",
        available_scopes=["odoo.readonly"],
        default_scopes=["odoo.readonly"],
    ),
    ConnectorScopeDefinition(
        connector_id="gmail",
        display_name="Gmail",
        available_scopes=["gmail.readonly", "gmail.metadata"],
        default_scopes=["gmail.readonly"],
    ),
    ConnectorScopeDefinition(
        connector_id="google_calendar",
        display_name="Google Calendar",
        available_scopes=["calendar.readonly", "calendar.events.metadata"],
        default_scopes=["calendar.readonly"],
    ),
    ConnectorScopeDefinition(
        connector_id="google_drive",
        display_name="Google Drive",
        available_scopes=["drive.readonly", "drive.metadata.readonly"],
        default_scopes=["drive.readonly"],
    ),
    ConnectorScopeDefinition(
        connector_id="whatsapp",
        display_name="WhatsApp",
        available_scopes=["whatsapp.messages.readonly", "whatsapp.profile.readonly"],
        default_scopes=["whatsapp.messages.readonly"],
    ),
    ConnectorScopeDefinition(
        connector_id="slack",
        display_name="Slack",
        available_scopes=["slack.channels.read", "slack.chat.read"],
        default_scopes=["slack.channels.read"],
    ),
    ConnectorScopeDefinition(
        connector_id="custom_http_api",
        display_name="Custom HTTP API",
        available_scopes=["http.readonly", "http.metadata"],
        default_scopes=["http.readonly"],
    ),
]
