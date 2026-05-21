from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectorDefinition(BaseModel):
    connector_id: str
    name: str
    status: str
    description: str
    required_config: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    safe_modes: list[str] = Field(default_factory=list)
    execution_enabled: bool = False
    real_execution_enabled: bool = False
    safety_notes: list[str] = Field(default_factory=list)


_CONNECTORS = [
    ConnectorDefinition(
        connector_id="odoo",
        name="Odoo",
        status="implemented",
        description="Read-only Odoo connector plus controlled R1/R2 pilot surfaces guarded by release safety flags.",
        required_config=["connection_id"],
        required_permissions=["read:business_objects", "read:metadata"],
        safe_modes=["read_only", "dry_run", "r1_pilot", "r2_pilot"],
        execution_enabled=False,
        real_execution_enabled=False,
        safety_notes=[
            "Generic Odoo writes are disabled.",
            "R3/R4 writes are disabled.",
            "Templates install as drafts and must pass review, compile, and approval gates.",
        ],
    ),
    ConnectorDefinition(
        connector_id="gmail",
        name="Gmail",
        status="placeholder",
        description="Placeholder connector for future lead-intake automation templates.",
        required_config=["oauth_connection_id"],
        required_permissions=["mail.readonly"],
        safe_modes=["catalog_only"],
        safety_notes=["No Gmail OAuth or execution is implemented."],
    ),
    ConnectorDefinition(
        connector_id="google_calendar",
        name="Google Calendar",
        status="placeholder",
        description="Placeholder connector for future follow-up scheduling templates.",
        required_config=["oauth_connection_id"],
        required_permissions=["calendar.readonly"],
        safe_modes=["catalog_only"],
        safety_notes=["No Calendar OAuth or execution is implemented."],
    ),
    ConnectorDefinition(
        connector_id="google_drive",
        name="Google Drive",
        status="placeholder",
        description="Placeholder connector for future document classification templates.",
        required_config=["oauth_connection_id"],
        required_permissions=["drive.readonly"],
        safe_modes=["catalog_only"],
        safety_notes=["No Drive OAuth or execution is implemented."],
    ),
    ConnectorDefinition(
        connector_id="whatsapp",
        name="WhatsApp",
        status="placeholder",
        description="Placeholder connector for future messaging workflow templates.",
        required_config=["business_account_id"],
        required_permissions=["messages.readonly"],
        safe_modes=["catalog_only"],
        safety_notes=["No WhatsApp API execution is implemented."],
    ),
    ConnectorDefinition(
        connector_id="slack",
        name="Slack",
        status="placeholder",
        description="Placeholder connector for future notification and intake templates.",
        required_config=["workspace_connection_id"],
        required_permissions=["channels.read"],
        safe_modes=["catalog_only"],
        safety_notes=["No Slack execution is implemented."],
    ),
    ConnectorDefinition(
        connector_id="custom_http_api",
        name="Custom HTTP API",
        status="placeholder",
        description="Placeholder connector for future controlled HTTP API integrations.",
        required_config=["base_url"],
        required_permissions=["read"],
        safe_modes=["catalog_only"],
        safety_notes=["No arbitrary HTTP execution runtime is implemented."],
    ),
]


class ConnectorCatalogService:
    def list_connectors(self) -> list[ConnectorDefinition]:
        return list(_CONNECTORS)

    def get_connector(self, connector_id: str) -> ConnectorDefinition | None:
        return next((connector for connector in _CONNECTORS if connector.connector_id == connector_id), None)
